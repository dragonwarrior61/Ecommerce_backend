from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class Damaged_goodBase(BaseModel):
    return_id: Optional[int] = None
    return_reason: Optional[str] = None
    return_date: Optional[datetime] = None
    product_ean: Optional[List[str]] = None
    product_id: Optional[List[int]] = None
    product_code: Optional[List[str]] = None
    quantity: Optional[List[int]] = None
    awb: Optional[str] = None
    user_id: Optional[int] = None
    
class Damaged_goodCreate(Damaged_goodBase):
    pass

class Damaged_goodRead(Damaged_goodBase):
    id:int

    class Config:
        orm_mode = True

class Damaged_goodUpdate(Damaged_goodBase):
    pass