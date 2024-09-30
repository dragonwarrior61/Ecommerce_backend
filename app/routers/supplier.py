from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import List
from app.database import get_db
from app.models.supplier import Supplier
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.supplier import SupplierCreate, SupplierRead, SupplierUpdate

router = APIRouter()

@router.post("/", response_model=SupplierRead)
async def create_supplier(supplier: SupplierCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    db_supplier = Supplier(**supplier.dict())
    db_supplier.user_id = user.id
    db.add(db_supplier)
    await db.commit()
    await db.refresh(db_supplier)
    return db_supplier

@router.get('/count')
async def get_suppliers_count(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Supplier).where(Supplier.user_id == user.id))
    db_suppliers = result.scalars().all()
    return len(db_suppliers)

@router.get("/", response_model=List[SupplierRead])
async def get_suppliers(
    user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Supplier).where(Supplier.user_id == user.id))
    db_suppliers = result.scalars().all()
    if db_suppliers is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return db_suppliers

@router.put("/{supplier_id}", response_model=SupplierRead)
async def update_supplier(supplier_id: int, supplier: SupplierUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Supplier).filter(Supplier.id == supplier_id, Supplier.user_id == user.id))
    db_supplier = result.scalars().first()
    if db_supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    for var, value in vars(supplier).items():
        setattr(db_supplier, var, value) if value is not None else None
    db.add(db_supplier)
    await db.commit()
    await db.refresh(db_supplier)
    return db_supplier

@router.delete("/{supplier_id}", response_model=SupplierRead)
async def delete_supplier(supplier_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Supplier).filter(Supplier.id == supplier_id, Supplier.user_id == user.id))
    supplier = result.scalars().first()
    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    await db.delete(supplier)
    await db.commit()
    return supplier
