from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.config import settings
from app.database import get_db
from app.models import Supplier
from app.routers.auth import get_team_admin_user
from app.schemas.supplier import SupplierCreate, SupplierRead, SupplierUpdate

router = APIRouter()

@router.post("/", response_model=SupplierRead)
async def create_supplier(
    supplier: SupplierCreate,
    user_id: int = Depends(get_team_admin_user),
    db: AsyncSession = Depends(get_db)
):
    db_supplier = Supplier(**supplier.model_dump())
    db_supplier.user_id = user_id
    settings.update_flag = 1
    try:
        db.add(db_supplier)
        await db.commit()
        await db.refresh(db_supplier)
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0

    return db_supplier

@router.get('/count')
async def get_suppliers_count(
    user_id: int = Depends(get_team_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Supplier).where(Supplier.user_id == user_id))
    db_suppliers = result.scalars().all()
    return len(db_suppliers)

@router.get("/", response_model=List[SupplierRead])
async def get_suppliers(
    user_id: int = Depends(get_team_admin_user), 
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Supplier).where(Supplier.user_id == user_id))
    db_suppliers = result.scalars().all()
    if db_suppliers is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return db_suppliers

@router.put("/{supplier_id}", response_model=SupplierRead)
async def update_supplier(
    supplier_id: int,
    supplier: SupplierUpdate,
    user_id: int = Depends(get_team_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Supplier).filter(Supplier.id == supplier_id, Supplier.user_id == user_id))
    db_supplier = result.scalars().first()
    if db_supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    for var, value in vars(supplier).items():
        setattr(db_supplier, var, value) if value is not None else None

    settings.update_flag = 1
    try:
        await db.commit()
        await db.refresh(db_supplier)
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
    return db_supplier

@router.delete("/{supplier_id}", response_model=SupplierRead)
async def delete_supplier(
    supplier_id: int,
    user_id: int = Depends(get_team_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Supplier).filter(
        Supplier.id == supplier_id,
        Supplier.user_id == user_id
    ))
    supplier = result.scalars().first()
    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")

    settings.update_flag = 1
    try:
        await db.delete(supplier)
        await db.commit()
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0

    return supplier
