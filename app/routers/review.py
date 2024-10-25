from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import List
from app.models.user import User
from app.routers.auth import get_current_user
from app.database import get_db
from app.models.review import Review
from app.models.team_member import Team_member
from app.schemas.review import ReviewCreate, ReviewRead, ReviewUpdate

router = APIRouter()

@router.post("/", response_model=ReviewRead)
async def create_review(review: ReviewCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
    db_review = Review(**review.dict())
    db_review.admin_id = user_id
    db.add(db_review)
    await db.commit()
    await db.refresh(db_review)
    return db_review

@router.get('/count')
async def get_reviews_count(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(Review).where(Review.admin_id == user_id))
    db_reviews = result.scalars().all()
    return len(db_reviews)

@router.get("/", response_model=List[ReviewRead])
async def get_reviews(
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
        
    result = await db.execute(select(Review).where(Review.admin_id == user_id))
    db_reviews = result.scalars().all()
    if db_reviews is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return db_reviews

@router.put("/{review_id}", response_model=ReviewRead)
async def update_review(review_id: int, review: ReviewUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(Review).filter(Review.id == review_id, Review.admin_id == user_id))
    db_review = result.scalars().first()
    if db_review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    for var, value in vars(review).items():
        setattr(db_review, var, value) if value is not None else None
    db.add(db_review)
    await db.commit()
    await db.refresh(db_review)
    return db_review

@router.delete("/{review_id}", response_model=ReviewRead)
async def delete_review(review_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role == -1:
        raise HTTPException(status_code=401, detail="Authentication error")
    
    if user.role != 4:
        result = await db.execute(select(Team_member).where(Team_member.user == user.id))
        db_team = result.scalars().first()
        user_id = db_team.admin
    else:
        user_id = user.id
        
    result = await db.execute(select(Review).filter(Review.id == review_id, Review.admin_id == user_id))
    review = result.scalars().first()
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    await db.delete(review)
    await db.commit()
    return review
