from pydantic import BaseModel
from typing import Optional, Union, Dict
from datetime import datetime

class ProfileBase(BaseModel):
    company: Optional[str] = None
    phone: Optional[str] = None
    country: Optional[str] = None
    avatar: Optional[Union[str, Dict[str, str]]] = None

class ProfileCreate(ProfileBase):
    pass

class ProfileUpdate(ProfileBase):
    pass

class ProfileRead(ProfileBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True

class UserProfileRead(BaseModel):
    id: int
    joined_day: Optional[str] = None
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    username: Optional[str] = None
    address: Optional[str] = None
    updated_at: Optional[datetime] = None
    last_login: Optional[str] = None
    profile: Optional[ProfileRead] = None
    access: Optional[list[str]] = None
    avatar: Optional[Union[str, Dict[str, str]]] = None
    initials: Optional[Union[str, Dict[str, str]]] = None

    class Config:
        from_attributes = True