from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import List
from app.database import get_db
from app.models.user import User
from app.models.user import User
from app.routers.auth import get_current_user
from app.models.team_member import Team_member
from app.schemas.team_member import Team_memberCreate, Team_memberRead, Team_memberUpdate
from app.config import settings

import logging

router = APIRouter()

@router.post("/", response_model=Team_memberRead)
async def create_team_member(team_member: Team_memberCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role != 4:
        raise HTTPException(status_code=401, detail="Authentication error")
    db_team_member = Team_member(**team_member.dict())
    db_team_member.admin = user.id
    user_id = db_team_member.user
    result = await db.execute(select(User).where(User.id == user_id))
    db_user = result.scalars().first()
    db_user.role = 1
    
    settings.update_flag = 1
    try:
        db.add(db_team_member)
        await db.commit()
        await db.refresh(db_team_member)
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
    
    return db_team_member

@router.get('/count')
async def get_team_members_count(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Team_member).where(Team_member.user == user.id))
    db_members = result.scalars().all()
    return len(db_members)

@router.get("/")
async def get_team_members(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
    
    result = await db.execute(select(Team_member).where(Team_member.admin == user_id))
    db_team = result.scalars().all()
    if db_team is None:
        raise HTTPException(status_code=404, detail="Team_member not found")
    
    user_data = []
    result = await db.execute(select(User).where(User.id == user_id))
    db_user = result.scalars().first()
    user_data.append(db_user)
    for member in db_team:
        result = await db.execute(select(User).where(User.id == member.user))
        db_user = result.scalars().first()
        user_data.append(db_user)
    return user_data

@router.put("/")
async def update_team_member(team_member: Team_memberUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    user = team_member.user
    role = team_member.role
    result = await db.execute(select(Team_member).where(Team_member.user == user, Team_member.user == user.id))
    db_team_member = result.scalars().first()
    if db_team_member is None:
        raise HTTPException(status_code=404, detail="Team_member not found")

    result = await db.execute(select(User).where(User.id == user))
    db_user = result.scalars().first()
    db_user.role = role
    
    settings.update_flag = 1
    try:
        await db.commit()
        await db.refresh(db_team_member)
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
    
    return db_team_member

@router.delete("/", response_model=Team_memberRead)
async def delete_team_member(user: int, admin: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Team_member).where(Team_member.admin == admin.id, Team_member.user == user))
    team_member = result.scalars().first()
    if team_member is None:
        raise HTTPException(status_code=404, detail="Team_member not found")
    
    settings.update_flag = 1
    try:
        await db.delete(team_member)
        await db.commit()
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
    
    return team_member
