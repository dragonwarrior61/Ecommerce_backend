from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, any_
from typing import List
from app.database import get_db
from app.models.user import User
from app.routers.auth import get_current_user
from app.models.billing_software import Billing_software
from app.schemas.billing_software import Billing_softwaresCreate, Billing_softwaresRead, Billing_softwaresUpdate
from app.config import settings

router = APIRouter()

@router.post("/", response_model=Billing_softwaresRead)
async def create_billing_software(billing_software: Billing_softwaresCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role != 4:
        raise HTTPException(status_code=401, detail="Authentication error")
    db_billing_software = Billing_software(**billing_software.dict())
    db_billing_software.user_id = user.id
    
    settings.update_flag = 1
    db.add(db_billing_software)
    try:
        await db.commit()
        await db.refresh(db_billing_software)
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
    return db_billing_software

@router.get('/count')
async def get_billing_software_count(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role != 4:
        raise HTTPException(status_code=401, detail="Authentication error")
    result = await db.execute(select(Billing_software).where(Billing_software.user_id == user.id))
    db_billing_softwares = result.scalars().all()
    return len(db_billing_softwares)

@router.get("/", response_model=List[Billing_softwaresRead])
async def get_billing_softwares(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role != 4:
        raise HTTPException(status_code=401, detail="Authentication error")
    result = await db.execute(select(Billing_software).where(Billing_software.user_id == user.id))
    db_billing_softwares = result.scalars().all()

    if db_billing_softwares is None:
        raise HTTPException(status_code=404, detail="Billing Software not found")
    
    return db_billing_softwares

@router.put("/{billing_software_id}", response_model=Billing_softwaresRead)
async def update_billing_software(billing_software_id: int, billing_software: Billing_softwaresUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role != 4:
        raise HTTPException(status_code=401, detail="Authentication error")
    result = await db.execute(select(Billing_software).where(Billing_software.id == billing_software_id, Billing_software.user_id == user.id))
    db_billing_software = result.scalars().first()
    if db_billing_software is None:
        raise HTTPException(status_code=404, detail="billing_software not found")
    for var, value in vars(billing_software).items():
        setattr(db_billing_software, var, value) if value is not None else None
    
    settings.update_flag = 1
    try:
        await db.commit()
        await db.refresh(db_billing_software)
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
        
    return db_billing_software

@router.delete("/{billing_software_id}", response_model=Billing_softwaresRead)
async def delete_billing_software(billing_software_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role != 4:
        raise HTTPException(status_code=401, detail="Authentication error")
    result = await db.execute(select(Billing_software).where(Billing_software.id == billing_software_id, Billing_software.user_id == user.id))
    billing_software = result.scalars().first()
    if billing_software is None:
        raise HTTPException(status_code=404, detail="billing_software not found")
    settings.update_flag = 1
    try:
        await db.delete(billing_software)
        await db.commit()
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
    return billing_software
