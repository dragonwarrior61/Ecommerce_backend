from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.config import settings
from app.database import get_db
from app.models import Warehouse
from app.routers.auth import get_team_admin_user
from app.schemas.warehouse import WarehouseCreate, WarehouseRead, WarehouseUpdate

router = APIRouter()

@router.post("/", response_model=WarehouseRead)
async def create_warehouse(
    warehouse: WarehouseCreate,
    user_id: int = Depends(get_team_admin_user),
    db: AsyncSession = Depends(get_db)
):
    db_warehouse = Warehouse(**warehouse.model_dump())
    db_warehouse.user_id = user_id
    settings.update_flag = 1
    try:
        db.add(db_warehouse)
        await db.commit()
        await db.refresh(db_warehouse)
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0

    return db_warehouse

@router.get('/count')
async def get_warehouses_count(user_id: int = Depends(get_team_admin_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Warehouse).where(Warehouse.user_id == user_id))
    db_warehouses = result.scalars().all()
    return len(db_warehouses)

@router.get("/", response_model=List[WarehouseRead])
async def get_warehouses(
    user_id: int = Depends(get_team_admin_user), 
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Warehouse).where(Warehouse.user_id == user_id))
    db_warehouses = result.scalars().all()
    if db_warehouses is None:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return db_warehouses

@router.put("/{warehouse_id}", response_model=WarehouseRead)
async def update_warehouse(
    warehouse_id: int,
    warehouse: WarehouseUpdate,
    user_id: int = Depends(get_team_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Warehouse).filter(
        Warehouse.id == warehouse_id,
        Warehouse.user_id == user_id
    ))
    db_warehouse = result.scalars().first()
    if db_warehouse is None:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    update_data = warehouse.dict(exclude_unset=True)  # Only update fields that are set
    for key, value in update_data.items():
        setattr(db_warehouse, key, value) if value is not None else None

    settings.update_flag = 1
    try:
        await db.commit()
        await db.refresh(db_warehouse)
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0

    return db_warehouse

@router.delete("/{warehouse_id}", response_model=WarehouseRead)
async def delete_warehouse(
    warehouse_id: int,
    user_id: int = Depends(get_team_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Warehouse).filter(
        Warehouse.id == warehouse_id,
        Warehouse.user_id == user_id
    ))
    warehouse = result.scalars().first()
    if warehouse is None:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    settings.update_flag = 1
    try:
        await db.delete(warehouse)
        await db.commit()
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0

    return warehouse
