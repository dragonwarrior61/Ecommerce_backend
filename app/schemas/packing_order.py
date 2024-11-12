from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class Packing_orderBase(BaseModel):
    order_id: Optional[int] = None
    awb_number: Optional[str] = None
    product_ean: Optional[List[str]] = None
    quantity: Optional[List[int]] = None
    order_quantity: Optional[List[int]] = None
    staff_id: Optional[int] = None
    pack_status: Optional[int] = None
    starting_time: Optional[datetime] = None
    ending_time: Optional[datetime] = None
    user_id: Optional[int] = None
    
class Packing_orderCreate(Packing_orderBase):
    pass

class Packing_orderRead(Packing_orderBase):
    id: int

    class Config:
        orm_mode = True

class Packing_orderUpdate(Packing_orderBase):
    pass