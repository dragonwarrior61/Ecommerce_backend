from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class Reverse_InvoiceBase(BaseModel):
    order_id: Optional[int] = None
    replacement_id: Optional[int] = None
    companyVatCode: Optional[str] = None
    seriesName: Optional[str] = None
    factura_number: Optional[str] = None
    storno_number: Optional[str] = None
    post: Optional[int] = None
    user_id: Optional[int] = None
    
class Reverse_InvoiceCreate(Reverse_InvoiceBase):
    pass

class Reverse_InvoiceRead(Reverse_InvoiceBase):
    id: int

    class Config:
        orm_mode = True

class Reverse_InvoiceUpdate(Reverse_InvoiceBase):
    pass