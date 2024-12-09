from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class ShipmentBase(BaseModel):
    title: Optional[str] = None
    create_date: Optional[datetime] = None
    delivery_date: Optional[datetime] = None
    type: Optional[str] = None
    status: Optional[str] = None
    warehouse: Optional[str] = None
    note: Optional[str] = None
    agent: Optional[str] = None
    awb: Optional[str] = None
    vat: Optional[Decimal] = None
    custom_taxes: Optional[Decimal] = None
    shipment_cost: Optional[Decimal] = None
    ean: Optional[List[str]] = None
    quantity: Optional[List[int]] = None
    item_per_box: Optional[List[int]] = None
    pdf_sent: Optional[List[bool]] = None
    pay_url: Optional[List[str]] = None
    tracking: Optional[List[str]] = None
    inland_cost: Optional[List[Decimal]] = None
    arrive_agent: Optional[List[bool]] = None
    wechat_group: Optional[List[str]] = None
    pp: Optional[List[str]] = None
    each_status: Optional[List[str]] = None
    box_number: Optional[List[int]] = None
    document: Optional[List[str]] = None
    date_added: Optional[List[datetime]] = None
    date_agent: Optional[List[datetime]] = None
    ship_id: Optional[List[str]] = None
    before: Optional[List[str]] = None
    user: Optional[List[int]] = None
    address: Optional[str] = None
    cnt: Optional[int] = None
    other_cost: Optional[List[Decimal]] = None
    target_day: Optional[int] = 90
    received: Optional[List[int]] = None
    price: Optional[List[Decimal]] = None
    each_note: Optional[List[str]] = None
    updated_at: Optional[datetime] = None
    arrived_date: Optional[datetime] = None
    ship_date: Optional[datetime] = None
    user_id: Optional[int] = None

class ShipmentCreate(ShipmentBase):
    pass

class ShipmentUpdate(ShipmentBase):
    pass

class ShipmentRead(ShipmentBase):
    id: int

    class Config:
        orm_mode = True