from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class InvoicesBase(BaseModel):
    replacement_id: Optional[int] = None
    order_id: Optional[int] = None
    companyVatCode: Optional[str] = None
    seriesName: Optional[str] = None
    client: Optional[str] = None
    usestock: Optional[bool] = None
    isdraft: Optional[bool] = None
    issueDate: Optional[datetime] = None
    mentions: Optional[str] = None
    observations: Optional[str] = None
    language: Optional[str] = None
    precision: Optional[int] = None
    useEstimateDetails: Optional[bool] = None
    estimate: Optional[str] = None
    currency: Optional[str] = None
    products: Optional[str] = None
    warehouseName: Optional[str] = None
    number: Optional[str] = None
    series: Optional[str] = None
    url: Optional[str] = None
    type: Optional[str] = None
    post: Optional[int] = None
    user_id: Optional[int] = None
    
class InvoicesCreate(InvoicesBase):
    pass

class InvoicesRead(InvoicesBase):
    id: int

    class Config:
        orm_mode = True

class InvoicesUpdate(InvoicesBase):
    pass