from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional

from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas.user import UserRead
from app.models import Team_member
from app.utils.security import (
    oauth2_scheme,
    create_access_token,
    create_refresh_token,
    verify_password
)

router = APIRouter()

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

async def update_last_logged_in(db: AsyncSession, user_id: int):
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if user:
        user.last_logged_in = datetime.utcnow()
        await db.commit()
        await db.refresh(user)
    return user

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("email")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).filter(User.email == token_data.email))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user

async def get_team_admin_user(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")

    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
    return user_id

@router.post("/verify_token", response_model=UserRead)
async def get_user(current_user: User = Depends(get_current_user)):
    return current_user

class UserInDB(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    role: Optional[int] = None
    hashed_password: str

class UserCredentials(BaseModel):
    email: str
    password: str

async def authenticate_user(db: AsyncSession, email: str, password: str):
    result = await db.execute(select(User).filter(User.email == email))
    user = result.scalars().first()
    if not user or not verify_password(password, user.hashed_password):
        return False
    return UserInDB(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        hashed_password=user.hashed_password
    )

@router.post("/token", response_model=Token)
async def login_for_access_token(credentials: UserCredentials, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "bearer"},
        )
    await update_last_logged_in(db, user.id)
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"email": user.email}, expires_delta=access_token_expires)
    refresh_token = create_refresh_token(data={"email": user.email}, expires_delta=refresh_token_expires)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@router.post("/refresh", response_model=Token)
async def refresh_access_token(refresh_token: str):
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("email")
        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        token_data = TokenData(email=email)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"email": token_data.email}, expires_delta=access_token_expires)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}
