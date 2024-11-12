from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Packing_ordersBase(BaseModel):
    order_id: Optional[int] = None
    awb_number: Optional[str] = None
    product_ean: Optional[str] = None
    quantity: Optional[int] = None
    staff_id: Optional[int] = None
    pack_status: Optional[int] = None
    pack_date: Optional[datetime] = None
    user_id: Optional[int] = None
    
class Packing_ordersCreate(Packing_ordersBase):
    pass

class Packing_ordersRead(Packing_ordersBase):
    id: int

    class Config:
        orm_mode = True

class Packing_ordersUpdate(Packing_ordersBase):
    pass