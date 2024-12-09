from pydantic import BaseModel, HttpUrl, EmailStr
from typing import Dict
from typing import Optional
from datetime import datetime

class NotificationBase(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    time: Optional[datetime] = None
    ean: str
    state: str = "warning"
    read: bool = False
    user_id: int = 1
    market_place: Optional[str] = None

class NotificationCreate(NotificationBase):
    pass

class NotificationUpdate(NotificationBase):
    pass

class NotificationRead(NotificationBase):
    title: str
    ean: str
    market_place: str

    class Config:
        orm_mode = True
        from_attributes = True
