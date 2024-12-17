from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.config import settings
from app.database import get_db
from app.models import Review
from app.routers.auth import get_team_admin_user
from app.schemas.review import ReviewCreate, ReviewRead, ReviewUpdate

router = APIRouter()

@router.post("/", response_model=ReviewRead)
async def create_review(review: ReviewCreate, user_id: int = Depends(get_team_admin_user), db: AsyncSession = Depends(get_db)):
    db_review = Review(**review.model_dump())
    db_review.admin_id = user_id

    settings.update_flag = 1
    try:
        db.add(db_review)
        await db.commit()
        await db.refresh(db_review)
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0

    return db_review

@router.get('/count')
async def get_reviews_count(user_id: int = Depends(get_team_admin_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Review).where(Review.admin_id == user_id))
    db_reviews = result.scalars().all()
    return len(db_reviews)

@router.get("/", response_model=List[ReviewRead])
async def get_reviews(
    user_id: int = Depends(get_team_admin_user), 
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Review).where(Review.admin_id == user_id))
    db_reviews = result.scalars().all()
    if db_reviews is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return db_reviews

@router.put("/{review_id}", response_model=ReviewRead)
async def update_review(
    review_id: int,
    review: ReviewUpdate,
    user_id: int = Depends(get_team_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Review).filter(Review.id == review_id, Review.admin_id == user_id))
    db_review = result.scalars().first()
    if db_review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    for var, value in vars(review).items():
        setattr(db_review, var, value) if value is not None else None

    settings.update_flag = 1
    try:
        db.add(db_review)
        await db.commit()
        await db.refresh(db_review)
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0

    return db_review

@router.delete("/{review_id}", response_model=ReviewRead)
async def delete_review(review_id: int, user_id: int = Depends(get_team_admin_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Review).filter(Review.id == review_id, Review.admin_id == user_id))
    review = result.scalars().first()
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")

    settings.update_flag = 1
    try:
        await db.delete(review)
        await db.commit()
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0

    return review
