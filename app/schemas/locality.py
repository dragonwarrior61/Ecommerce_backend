from pydantic import BaseModel, HttpUrl, EmailStr
from typing import Dict
from typing import Optional
from datetime import datetime

class LocalityBase(BaseModel):
    id: int
    name: Optional[str] = None
    name_latin: Optional[str] = None
    region1: Optional[str] = None
    region2: Optional[str] = None
    region3: Optional[str] = None
    region1_latin: Optional[str] = None
    region2_latin: Optional[str] = None
    region3_latin: Optional[str] = None
    geoid: Optional[int] = None
    modified: Optional[datetime] = None
    country_code: Optional[str] = None
    localtity_marketplace: Optional[str] = None
    user_id: Optional[int] = None

class LocalityCreate(LocalityBase):
    pass

class LocalityUpdate(LocalityBase):
    pass

class LocalityRead(LocalityBase):
    id: int
    localtity_marketplace: str

    class Config:
        orm_mode = True
        from_attributes = True
