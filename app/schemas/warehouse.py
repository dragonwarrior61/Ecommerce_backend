from pydantic import BaseModel
from typing import Optional, List

class WarehouseBase(BaseModel):
    name : Optional[str] = None
    sender_name: Optional[str] = None
    sender_contact: Optional[str] = None
    phone1: Optional[str] = None
    phone2: Optional[str] = None
    legal_entity: bool = False
    locality_id: Optional[str] = None
    street: Optional[str] = None
    zipcode: Optional[str] = None
    user_id: Optional[int] = None

class WarehouseCreate(WarehouseBase):
    pass

class WarehouseUpdate(WarehouseBase):
    pass

class WarehouseRead(WarehouseBase):
    id: int

    class Config:
        orm_mode = True