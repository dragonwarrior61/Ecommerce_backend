from pydantic import BaseModel
from typing import Optional

class SupplierBase(BaseModel):
    group: Optional[str] = None
    name: Optional[str] = None
    wechat: Optional[str] = None
    user_id: Optional[int] = None

class SupplierCreate(SupplierBase):
    pass

class SupplierRead(SupplierBase):
    id: int

    class Config:
        orm_mode = True

class SupplierUpdate(SupplierBase):
    pass