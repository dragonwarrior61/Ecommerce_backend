from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ReturnsBase(BaseModel):
    emag_id: Optional[int] = None
    order_id: int
    type: Optional[int] = None
    customer_name: Optional[str] = None
    customer_company: Optional[str] = None
    customer_phone: Optional[str] = None
    products: Optional[List[str]] = None
    quantity: Optional[List[int]] = None
    observations: Optional[List[str]] = None
    pickup_address: Optional[str] = None
    return_reason: Optional[str] = None
    return_type: Optional[int] = None
    replacement_product_emag_id: Optional[int] = None
    replacement_product_id: Optional[int] = None
    replacement_product_name: Optional[str] = None
    replacement_product_quantity: Optional[int] = None
    date: Optional[datetime] = None
    request_status: Optional[int] = None
    return_market_place: Optional[str] = None
    awb: Optional[str] = None
    awb_status: Optional[str] = None
    user_id: Optional[int] = None

class ReturnsCreate(ReturnsBase):
    pass

class ReturnsRead(ReturnsBase):
    order_id: int
    return_market_place:str

    class Config:
        orm_mode = True

class ReturnsUpdate(ReturnsBase):
    pass