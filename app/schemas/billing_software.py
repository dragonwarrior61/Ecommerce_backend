from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class Billing_softwaresBase(BaseModel):
    user_id: Optional[int] = None
    site_domain: Optional[str] = None
    company_name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    registration_number: Optional[str] = None
    warehouse_name: Optional[str] = None
    
class Billing_softwaresCreate(Billing_softwaresBase):
    pass

class Billing_softwaresRead(Billing_softwaresBase):
    id:int

    class Config:
        orm_mode = True

class Billing_softwaresUpdate(Billing_softwaresBase):
    pass