from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.config import settings
from app.database import get_db
from app.models import Temp_product
from app.routers.auth import get_team_admin_user
from app.schemas.temp_product import Temp_productCreate, Temp_productRead, Temp_productUpdate

router = APIRouter()

@router.post("/", response_model=Temp_productRead)
async def create_temp_product(
    temp_product: Temp_productCreate,
    user_id: int = Depends(get_team_admin_user),
    db: AsyncSession = Depends(get_db)
):
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
async def get_temp_products_count(user_id: int = Depends(get_team_admin_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Temp_product).where(Temp_product.user_id == user_id))
    db_temp_products = result.scalars().all()
    return len(db_temp_products)

@router.get("/", response_model=List[Temp_productRead])
async def get_temp_products(
    user_id: int = Depends(get_team_admin_user), 
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Temp_product).where(Temp_product.user_id == user_id))
    db_temp_products = result.scalars().all()
    if db_temp_products is None:
        raise HTTPException(status_code=404, detail="temp_product not found")
    return db_temp_products

@router.put("/{temp_product_id}", response_model=Temp_productRead)
async def update_temp_product(
    temp_product_id: int,
    temp_product: Temp_productUpdate,
    user_id: int = Depends(get_team_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Temp_product).filter(
        Temp_product.id == temp_product_id,
        Temp_product.user_id == user_id
    ))
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
async def delete_temp_product(
    temp_product_id: int,
    user_id: int = Depends(get_team_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Temp_product).filter(
        Temp_product.id == temp_product_id,
        Temp_product.user_id == user_id
    ))
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
