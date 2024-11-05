from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, any_, or_
from typing import List
from app.database import get_db
from app.models.user import User
from app.routers.auth import get_current_user
from app.models.internal_product import Internal_Product
from app.models.damaged_good import Damaged_good
from app.models.team_member import Team_member
from app.schemas.damaged_good import Damaged_goodCreate, Damaged_goodRead, Damaged_goodUpdate
from app.config import settings

router = APIRouter()

@router.post("/", response_model=Damaged_goodRead)
async def create_damaged_good(damaged_good: Damaged_goodCreate, db: AsyncSession = Depends(get_db)):
    db_damaged_good = Damaged_good(**damaged_good.dict())
    result = await db.execute(select(Damaged_good).where(Damaged_good.return_id == db_damaged_good.return_id))
    damaged_good = result.scalars().first()
    if damaged_good:
        return damaged_good
    product_ean_list = db_damaged_good.product_ean
    for i in range(len(product_ean_list)):
        ean = product_ean_list[i]
        result = await db.execute(select(Internal_Product).where(Internal_Product.ean == ean))
        product = result.scalars().first()
        if product is None:
            continue
        if product.damaged_goods:
            product.damaged_goods = product.damaged_goods + db_damaged_good.quantity[i]
        else:
            product.damaged_goods = db_damaged_good.quantity[i]
    first_ean = product_ean_list[0]
    result = await db.execute(select(Internal_Product).where(Internal_Product.ean == first_ean))
    db_internal_product = result.scalars().first()
    user_id = db_internal_product.user_id
    db_damaged_good.user_id = user_id
    
    settings.update_flag = 1
    try:
        db.add(db_damaged_good)
        await db.commit()
        await db.refresh(db_damaged_good)
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
    return db_damaged_good

@router.get('/count')
async def get_damaged_good_count(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(Damaged_good).where(Damaged_good.user_id == user_id))
    damaged_goods = result.scalars().all()
    return len(damaged_goods)

@router.get("/", response_model=List[Damaged_goodRead])
async def get_damaged_goods(
    page: int = Query(1, ge=1, description="Page number"),
    itmes_per_page: int = Query(50, ge=1, le=100, description="Number of items per page"),
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
        
    offset = (page - 1) * itmes_per_page
    result = await db.execute(select(Damaged_good).where(Damaged_good.user_id == user_id).offset(offset).limit(itmes_per_page))
    db_damaged_goods = result.scalars().all()
    if db_damaged_goods is None:
        raise HTTPException(status_code=404, detail="damaged_good not found")
    return db_damaged_goods

@router.get("/{damaged_good_id}", response_model=Damaged_goodRead)
async def get_damaged_good(damaged_good_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(Damaged_good).where(Damaged_good.id == damaged_good_id, Damaged_good.user_id == user_id))
    db_damaged_good = result.scalars().first()
    return db_damaged_good

@router.put("/{damaged_good_id}", response_model=Damaged_goodRead)
async def update_damaged_good(damaged_good_id: int, damaged_good: Damaged_goodUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(Damaged_good).where(Damaged_good.id == damaged_good_id, Damaged_good.user_id == user_id))
    db_damaged_good = result.scalars().first()
    if db_damaged_good is None:
        raise HTTPException(status_code=404, detail="damaged_good not found")
    for var, value in vars(damaged_good).items():
        setattr(db_damaged_good, var, value) if value is not None else None
    
    settings.update_flag = 1
    try:
        await db.commit()
        await db.refresh(db_damaged_good)
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
    return db_damaged_good

@router.delete("/{damaged_good_id}", response_model=Damaged_goodRead)
async def delete_damaged_good(damaged_good_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(Damaged_good).where(Damaged_good.id == damaged_good_id, Damaged_good.user_id == user_id))
    damaged_good = result.scalars().first()
    if damaged_good is None:
        raise HTTPException(status_code=404, detail="damaged_good not found")

    settings.update_flag = 1
    try:
        await db.delete(damaged_good)
        await db.commit()
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
    return damaged_good
