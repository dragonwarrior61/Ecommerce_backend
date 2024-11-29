# app/schemas/awb.py
from pydantic import BaseModel
from enum import Enum
from typing import Optional, List
from decimal import Decimal
from datetime import datetime

class AWBBase(BaseModel):
    order_id: Optional[int] = None
    number: Optional[int] = 0
    sender_name: Optional[str] = None
    sender_phone1: Optional[str] = None
    sender_phone2: Optional[str] = None
    sender_locality_id: Optional[int] = None
    sender_street: Optional[str] = None
    sender_zipcode: Optional[str] = None
    receiver_name: Optional[str] = None
    receiver_contact: Optional[str] = None
    receiver_phone1: Optional[str] = None
    receiver_phone2: Optional[str] = None
    receiver_legal_entity: Optional[int] = None
    receiver_locality_id: Optional[int] = None
    receiver_street: Optional[str] = None
    receiver_zipcode: Optional[str] = None
    locker_id: Optional[str] = None
    is_oversize: Optional[int] = None
    insured_value: Optional[Decimal] = None
    weight: Optional[Decimal] = None
    envelope_number: Optional[int] = None
    parcel_number: Optional[int] = None
    observation: Optional[str] = None
    cod: Optional[Decimal] = None
    courier_account_id: Optional[int] = None
    pickup_and_return: Optional[int] = None
    saturday_delivery: Optional[int] = None
    sameday_delivery: Optional[int] = None
    dropoff_locker: Optional[int] = None
    reservation_id: Optional[int] = None
    courier_id: Optional[int] = None
    courier_name: Optional[str] = None
    awb_number: Optional[str] = None
    awb_barcode: Optional[str]= None
    awb_marketplace: Optional[str] = None
    awb_status: Optional[int] = 0
    awb_date: Optional[datetime] = None
    awb_trigger: Optional[str] = None
    pickedup: Optional[bool] = False
    awb_creation_date: Optional[str] = None
    awb_status_update_time: Optional[datetime] = None
    length: Optional[Decimal] = None
    width: Optional[Decimal] = None
    height: Optional[Decimal] = None
    user_id: Optional[int] = None
    ean_list: Optional[List[str]] = None
    

class AWBCreate(AWBBase):
    pass

class AWBUpdate(AWBBase):
    pass

class AWBRead(AWBBase):
    order_id: int
    number: int

    class Config:
        orm_mode = True

# class ObservationFieldEnum(str, Enum):
#     EAN = "EAN"
#     SKU = "SKU"
#     EAN_SKU = "EAN_SKU"

# class AWBCreate(AWBBase):
#     observation_field: ObservationFieldEnum
