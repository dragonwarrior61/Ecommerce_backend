from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

class OrderBase(BaseModel):
    vendor_name: Optional[str] = None
    type: Optional[int] = None
    date: Optional[datetime] = None
    payment_mode: Optional[str] = None
    detailed_payment_method: Optional[str] = None
    delivery_mode: Optional[str] = None
    status: Optional[int] = None
    payment_status: Optional[int] = None
    customer_id: Optional[int] = None
    product_id: Optional[List[str]] = None
    quantity: Optional[List[int]] = None
    initial_quantity: Optional[List[int]] = None
    sale_price: Optional[List[float]] = None
    shipping_tax: Optional[float] = None
    shipping_tax_voucher_split: Optional[str] = None
    vouchers: Optional[str] = None
    proforms: Optional[str] = None
    attachments: Optional[str] = None  # JSON field to List[dict]
    shipping_address: Optional[str] = None
    cashed_co: Optional[float] = None
    cashed_cod: Optional[float] = None
    refunded_amount: Optional[float] = None
    is_complete: Optional[int] = None  # Corrected to bool
    cancellation_request: Optional[str] = None
    cancellation_reason: Optional[str] = None
    refund_status: Optional[str] = None
    maximum_date_for_shipment: Optional[datetime] = None
    late_shipment: Optional[int] = None
    flags: Optional[str] = None  # JSON field to List[dict]
    emag_club: Optional[int] = None  # Corrected to bool
    finalization_date: Optional[datetime] = None
    details: Optional[str] = None  # JSON field to List[dict]
    payment_mode_id: Optional[int] = None
    order_market_place: Optional[str] = None
    mkt_id: Optional[int] = None
    name: Optional[str] = None
    company: Optional[str] = None
    gender: Optional[str] = None
    phone_1: Optional[str] = None
    billing_name: Optional[str] = None
    billing_phone: Optional[str] = None
    billing_country: Optional[str] = None
    billing_suburb: Optional[str] = None
    billing_city: Optional[str] = None
    billing_locality_id: Optional[str] = None
    billing_street: Optional[str] = None
    shipping_country: Optional[str] = None
    shipping_suburb: Optional[str] = None
    shipping_city: Optional[str] = None
    shipping_locality_id: Optional[str] = None  # JSON field to List[dict]
    shipping_contact: Optional[str] = None
    shipping_phone: Optional[str] = None
    shipping_street: Optional[str] = None
    created: Optional[datetime] = None  # Corrected to bool
    modified: Optional[datetime] = None
    legal_entity: Optional[int] = None
    is_vat_payer: Optional[int] = None
    code: Optional[str] = None
    bank: Optional[str] = None
    iban: Optional[str] = None
    email: Optional[str] = None
    product_voucher_split: Optional[List[str]] = None
    registration_number: Optional[str] = None
    update_time: Optional[datetime] = None
    user_id: Optional[int] = None

class OrderCreate(OrderBase):
    pass

class OrderUpdate(OrderBase):
    pass

class OrderRead(OrderBase):
    id: int
    order_market_place: str

    class Config:
        orm_mode = True
