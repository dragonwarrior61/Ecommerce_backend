from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class Team_memberBase(BaseModel):
    admin: Optional[int] = None
    user: Optional[int] = None

class Team_memberCreate(Team_memberBase):
    pass

class Team_memberRead(Team_memberBase):
    id: int
    class Config:
        orm_mode = True
        from_attributes = True

class Team_memberUpdate(Team_memberBase):
    role: int
    pass
