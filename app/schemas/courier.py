from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class CouriersBase(BaseModel):
    account_id: int
    account_display_name: Optional[str] = None
    courier_account_type: Optional[int] = None
    courier_name: Optional[str] = None
    courier_account_properties: Optional[str] = None
    created: Optional[datetime] = None
    status: Optional[int] = None
    market_place: str
    user_id: Optional[int] = None

class CouriersRead(CouriersBase):
    account_id: int
    market_place: str

    class Config:
        orm_mode = True
