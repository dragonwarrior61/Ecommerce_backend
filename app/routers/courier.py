from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.database import get_db
from app.models import Courier
from app.routers.auth import get_team_admin_user
from app.schemas.courier import CouriersRead

router = APIRouter()

@router.get("/", response_model=List[CouriersRead])
async def get_couriers(
    user_id: int = Depends(get_team_admin_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Courier).where(Courier.user_id == user_id))
    db_couriers = result.scalars().all()
    if db_couriers is None:
        raise HTTPException(status_code=404, detail="couriers not found")
    return db_couriers
