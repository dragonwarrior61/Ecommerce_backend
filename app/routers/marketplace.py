from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.marketplace import Marketplace
from app.models.user import User
from app.routers.auth import get_current_user
from app.database import get_db
from app.schemas.marketplace import MarketplaceCreate, MarketplaceUpdate, MarketplaceRead
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pydantic import ValidationError
from app.config import settings

async def create_marketplace(db: AsyncSession, marketplace: MarketplaceCreate, user: User):
    if user.role != 4:
        raise HTTPException(status_code=401, detail="Authentication error")
    db_marketplace = Marketplace(**marketplace.dict())
    db_marketplace.user_id = user.id
    
    settings.update_flag = 1
    try:
        db.add(db_marketplace)
        await db.commit()
        await db.refresh(db_marketplace)
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
    
    return {"msg": "success"}

async def get_marketplace(db: AsyncSession, marketplace_id: int, user: User):
    result = await db.execute(select(Marketplace).filter(Marketplace.id == marketplace_id, Marketplace.user_id == user.id))
    return result.scalars().first()

async def get_marketplaces(db: AsyncSession, user: User, skip: int = 0, limit: int = 10):
    result = await db.execute(select(Marketplace).where(Marketplace.user_id == user.id).offset(skip).limit(limit))
    return result.scalars().all()

async def update_marketplace(db: AsyncSession, marketplace_id: int, marketplace: MarketplaceUpdate, user: User):
    db_marketplace = await get_marketplace(db, marketplace_id, user)
    if db_marketplace is None:
        return None
    for key, value in marketplace.dict().items():
        setattr(db_marketplace, key, value) if value is not None else None
    
    settings.update_flag = 1
    try:
        await db.commit()
        await db.refresh(db_marketplace)
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
    
    return db_marketplace

async def delete_marketplace(db: AsyncSession, marketplace_id: int, user: User):
    db_marketplace = await get_marketplace(db, marketplace_id, user)
    if db_marketplace is None:
        return None
    
    settings.update_flag = 1
    try:
        await db.delete(db_marketplace)
        await db.commit()
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0
    return db_marketplace

router = APIRouter()

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_new_marketplace(marketplace: MarketplaceCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    try:
        return await create_marketplace(db, marketplace, user)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.errors())
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

@router.get("/{marketplace_id}", response_model=MarketplaceRead)
async def read_marketplace(marketplace_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    marketplace = await get_marketplace(db, marketplace_id, user)
    if marketplace is None:
        raise HTTPException(status_code=404, detail="Marketplace not found")
    return marketplace

@router.get("/", response_model=List[MarketplaceRead])
async def read_marketplaces(skip: int = 0, limit: int = 10, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await get_marketplaces(db, user, skip=skip, limit=limit)

@router.put("/{marketplace_id}", response_model=MarketplaceRead)
async def update_existing_marketplace(marketplace_id: int, marketplace: MarketplaceUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    updated_marketplace = await update_marketplace(db, marketplace_id, marketplace, user)
    if updated_marketplace is None:
        raise HTTPException(status_code=404, detail="Marketplace not found")
    return updated_marketplace

@router.delete("/{marketplace_id}")
async def delete_existing_marketplace(marketplace_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    deleted_marketplace = await delete_marketplace(db, marketplace_id, user)
    if deleted_marketplace is None:
        raise HTTPException(status_code=404, detail="Marketplace not found")
    return {"msg": "success"}