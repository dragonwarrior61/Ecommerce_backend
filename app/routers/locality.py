from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.locality import Locality
from app.models.user import User
from app.routers.auth import get_current_user
from app.database import get_db
from app.schemas.locality import LocalityCreate, LocalityUpdate, LocalityRead
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pydantic import ValidationError
from app.config import settings

async def create_locality(db: AsyncSession, locality: LocalityCreate):
    db_locality = Locality(**locality.dict())
    
    settings.update_flag = 1
    db.add(db_locality)
    await db.commit()
    await db.refresh(db_locality)
    settings.update_flag = 0
    return {"msg": "success"}

async def get_locality(db: AsyncSession, locality_id: int):
    result = await db.execute(select(Locality).filter(Locality.id == locality_id))
    return result.scalars().first()

async def get_localitys(db: AsyncSession, skip: int = 0, limit: int = 10):
    result = await db.execute(select(Locality).offset(skip).limit(limit))
    return result.scalars().all()

async def update_locality(db: AsyncSession, locality_id: int, locality: LocalityUpdate):
    db_locality = await get_locality(db, locality_id)
    if db_locality is None:
        return None
    for key, value in locality.dict().items():
        setattr(db_locality, key, value) if value is not None else None
        
    settings.update_flag = 1
    await db.commit()
    await db.refresh(db_locality)
    settings.update_flag = 0
    
    return db_locality

async def delete_locality(db: AsyncSession, locality_id: int):
    db_locality = await get_locality(db, locality_id)
    if db_locality is None:
        return None
    
    settings.update_flag = 1
    await db.delete(db_locality)
    await db.commit()
    settings.update_flag = 0
    
    return db_locality

router = APIRouter()

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_new_locality(locality: LocalityCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await create_locality(db, locality)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.errors())
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

@router.get("/{locality_id}", response_model=LocalityRead)
async def read_locality(locality_id: int, db: AsyncSession = Depends(get_db)):
    locality = await get_locality(db, locality_id)
    if locality is None:
        raise HTTPException(status_code=404, detail="Locality not found")
    return locality

@router.get("/", response_model=List[LocalityRead])
async def read_localitys(skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db)):
    return await get_localitys(db, skip=skip, limit=limit)

@router.put("/{locality_id}", response_model=LocalityRead)
async def update_existing_locality(locality_id: int, locality: LocalityUpdate, db: AsyncSession = Depends(get_db)):
    updated_locality = await update_locality(db, locality_id, locality)
    if updated_locality is None:
        raise HTTPException(status_code=404, detail="Locality not found")
    return updated_locality

@router.delete("/{locality_id}")
async def delete_existing_locality(locality_id: int, db: AsyncSession = Depends(get_db)):
    deleted_locality = await delete_locality(db, locality_id)
    if deleted_locality is None:
        raise HTTPException(status_code=404, detail="Locality not found")
    return {"msg": "success"}