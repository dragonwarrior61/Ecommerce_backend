from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, any_
from typing import List
from app.database import get_db
from app.models.replacement import Replacement
from app.schemas.replacement import ReplacementsCreate, ReplacementsRead, ReplacementsUpdate

router = APIRouter()

@router.post("/", response_model=ReplacementsRead)
async def create_replacement(replacement: ReplacementsCreate, db: AsyncSession = Depends(get_db)):
    db_replacement = Replacement(**replacement.dict())
    order_id = db_replacement.order_id
    result = await db.execute(select(Replacement).where(Replacement.order_id == order_id))
    replacements = result.scalars().all()
    count = len(replacements)
    db_replacement.number = count + 1
    db.add(db_replacement)
    await db.commit()
    await db.refresh(db_replacement)
    return db_replacement

@router.get('/count')
async def get_replacement_count(db: AsyncSession = Depends(get_db)):
    result = await db.execute(func.count(Replacement.id))
    count = result.scalar()
    return count

@router.get("/", response_model=List[ReplacementsRead])
async def get_replacements(
    page: int = Query(1, ge=1, description="Page number"),
    itmes_per_page: int = Query(50, ge=1, le=100, description="Number of items per page"),
    db: AsyncSession = Depends(get_db)
):
    offset = (page - 1) * itmes_per_page
    result = await db.execute(select(Replacement).offset(offset).limit(itmes_per_page))
    db_replacements = result.scalars().all()
    if db_replacements is None:
        raise HTTPException(status_code=404, detail="replacement not found")
    return db_replacements

@router.get("/{replacement_id}", response_model=ReplacementsRead)
async def get_replacement(replacement_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Replacement).filter(Replacement.id == replacement_id))
    db_replacement = result.scalars().first()
    return db_replacement

@router.put("/{replacement_id}", response_model=ReplacementsRead)
async def update_replacement(replacement_id: int, replacement: ReplacementsUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Replacement).filter(Replacement.id == replacement_id))
    db_replacement = result.scalars().first()
    if db_replacement is None:
        raise HTTPException(status_code=404, detail="replacement not found")
    for var, value in vars(replacement).items():
        setattr(db_replacement, var, value) if value else None
    await db.commit()
    await db.refresh(db_replacement)
    return db_replacement

@router.delete("/{replacement_id}", response_model=ReplacementsRead)
async def delete_replacement(replacement_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Replacement).filter(Replacement.id == replacement_id))
    replacement = result.scalars().first()
    if replacement is None:
        raise HTTPException(status_code=404, detail="replacement not found")
    await db.delete(replacement)
    await db.commit()
    return replacement