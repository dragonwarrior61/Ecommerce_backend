from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import List
from app.models.user import User
from app.routers.auth import get_current_user
from app.database import get_db
from app.models.temp_product import Temp_product
from app.models.team_member import Team_member
from app.schemas.temp_product import Temp_productCreate, Temp_productRead, Temp_productUpdate
from app.config import settings

router = APIRouter()

@router.post("/", response_model=Temp_productRead)
async def create_temp_product(temp_product: Temp_productCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    db_temp_product = Temp_product(**temp_product.dict())
    db_temp_product.user_id = user_id
    
    settings.update_flag = 1
    try:
        db.add(db_temp_product)
        await db.commit()
        await db.refresh(db_temp_product)
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
    return db_temp_product

@router.get('/count')
async def get_temp_products_count(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(Temp_product).where(Temp_product.user_id == user_id))
    db_temp_products = result.scalars().all()
    return len(db_temp_products)

@router.get("/", response_model=List[Temp_productRead])
async def get_temp_products(
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
        
    result = await db.execute(select(Temp_product).where(Temp_product.user_id == user_id))
    db_temp_products = result.scalars().all()
    if db_temp_products is None:
        raise HTTPException(status_code=404, detail="temp_product not found")
    return db_temp_products

@router.put("/{temp_product_id}", response_model=Temp_productRead)
async def update_temp_product(temp_product_id: int, temp_product: Temp_productUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(Temp_product).filter(Temp_product.id == temp_product_id, Temp_product.user_id == user_id))
    db_temp_product = result.scalars().first()
    if db_temp_product is None:
        raise HTTPException(status_code=404, detail="temp_product not found")
    for var, value in vars(temp_product).items():
        setattr(db_temp_product, var, value) if value is not None else None
    
    settings.update_flag = 1
    try:
        await db.commit()
        await db.refresh(db_temp_product)
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
    
    return db_temp_product

@router.delete("/{temp_product_id}", response_model=Temp_productRead)
async def delete_temp_product(temp_product_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(Temp_product).filter(Temp_product.id == temp_product_id, Temp_product.user_id == user_id))
    temp_product = result.scalars().first()
    if temp_product is None:
        raise HTTPException(status_code=404, detail="temp_product not found")
    
    settings.update_flag = 1
    try:
        await db.delete(temp_product)
        await db.commit()
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
    return temp_product
