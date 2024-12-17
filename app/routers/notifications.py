import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.config import settings
from app.database import get_db
from app.models import Notification, User
from app.routers.auth import get_current_user, get_team_admin_user
from app.schemas.notifications import NotificationCreate, NotificationUpdate, NotificationRead

async def create_notification(db: AsyncSession, notifications: NotificationCreate, user_id: int):
    db_notification = Notification(**notifications.model_dump())
    db_notification.user_id = user_id
    settings.update_flag = 1
    try:
        db.add(db_notification)
        await db.commit()
        await db.refresh(db_notification)
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0

    return {"msg": "success"}

async def get_notification(db: AsyncSession, notification_id: int, user_id: int):
    result = await db.execute(select(Notification).filter(Notification.id == notification_id, Notification.user_id == user_id))
    return result.scalars().first()

async def get_notifications(db: AsyncSession, user_id: int):
    result = await db.execute(select(Notification).where(Notification.user_id == user_id))
    notifications = result.scalars().all()
    return notifications

async def update_notification(db: AsyncSession, notification_id: int, notification: NotificationUpdate, user_id: int):
    db_notification = await get_notification(db, notification_id, user_id)
    if db_notification is None:
        return None
    update_data = notification.dict(exclude_unset=True)  # Only update fields that are set
    for key, value in update_data.items():
        setattr(notification, key, value) if value is not None else None

    settings.update_flag = 1
    try:
        await db.commit()
        await db.refresh(db_notification)
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0

    return db_notification

async def delete_notification(db: AsyncSession, notification_id: int, user_id: int):
    db_notification = await get_notification(db, notification_id, user_id)
    if db_notification is None:
        return None

    settings.update_flag = 1
    try:
        await db.delete(db_notification)
        await db.commit()
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0

    return db_notification

router = APIRouter()

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_new_notification(notifications: NotificationCreate, user_id: int = Depends(get_team_admin_user), db: AsyncSession = Depends(get_db)):
    try:
        return await create_notification(db, notifications, user_id)
    except ValidationError as e:
        logging.error(f"Validation error: {e.errors()}")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.errors())
    except Exception as e:
        logging.error(f"Error creating notifications: {e}")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

@router.get("/", response_model=List[NotificationRead])
async def read_notifications(user_id: int = Depends(get_team_admin_user), db: AsyncSession = Depends(get_db)):
    return await get_notifications(db, user_id)

@router.get("/{notification_id}", response_model=NotificationRead)
async def read_notification(notification_id: int, user_id: int = Depends(get_team_admin_user), db: AsyncSession = Depends(get_db)):
    notifications = await get_notification(db, notification_id, user_id)
    if notifications is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notifications

@router.get("/read/{notification_id}", response_model=NotificationRead)
async def read_notification(notification_id: int, user: User = Depends(get_current_user), db:AsyncSession = Depends(get_db)):
    result = await db.execute(select(Notification).where(Notification.id == notification_id, Notification.user_id == user.id))
    db_notification = result.scalars().first()
    db_notification.read = True

    settings.update_flag = 1
    try:
        await db.commit()
        await db.refresh(db_notification)
    except Exception as e:
        db.rollback()
    finally:
        settings.update_flag = 0

    return db_notification

@router.put("/{notification_id}", response_model=NotificationRead)
async def update_existing_notification(
    notification_id: int,
    notifications: NotificationUpdate,
    user_id: int = Depends(get_team_admin_user),
    db: AsyncSession = Depends(get_db)
):
    updated_notification = await update_notification(db, notification_id, notifications, user_id)
    if updated_notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return updated_notification

@router.delete("/{notification_id}")
async def delete_existing_notification(notification_id: int, user_id: int = Depends(get_team_admin_user), db: AsyncSession = Depends(get_db)):
    deleted_notification = await delete_notification(db, notification_id, user_id)
    if deleted_notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"msg": "success"}