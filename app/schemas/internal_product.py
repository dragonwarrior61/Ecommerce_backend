from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal
from datetime import datetime

class Internal_ProductBase(BaseModel):
    id: Optional[int] = None
    ean: Optional[str] = None
    part_number_key: Optional[str] = None
    product_code: Optional[str] = None
    product_name: Optional[str] = None
    model_name: Optional[str] = None
    buy_button_rank: Optional[int] = None
    price: Optional[Decimal] = None
    sale_price: Optional[Decimal] = None
    ean: str
    image_link: Optional[str] = None
    barcode_title: Optional[str] = None
    masterbox_title: Optional[str] = None
    link_address_1688: Optional[str] = None
    price_1688: Optional[Decimal] = None
    variation_name_1688: Optional[str] = None
    pcs_ctn: Optional[str] = None
    weight: Optional[Decimal] = None
    volumetric_weight: Optional[Decimal] = None
    dimensions: Optional[str] = None
    supplier_id: Optional[int] = None
    english_name: Optional[str] = None
    romanian_name: Optional[str] = None
    material_name_en: Optional[str] = None
    material_name_ro: Optional[str] = None
    hs_code: Optional[str] = None
    battery: Optional[bool] = None
    default_usage: Optional[str] = None
    production_time: Optional[Decimal] = None
    discontinued: Optional[bool] = None
    stock: Optional[int] = None
    smartbill_stock: Optional[int] = None
    orders_stock: Optional[int] = None
    damaged_goods: Optional[int] = None
    warehouse_id: Optional[int] = None
    internal_shipping_price: Optional[Decimal] = None
    observation: Optional[str] = None
    short_product_name: Optional[str] = None
    market_place: Optional[List[str]] = None
    sync_stock_time: Optional[datetime] = None
    smartbill_stock_time: Optional[datetime] = None
    user_id: Optional[int] = None

class Internal_ProductCreate(Internal_ProductBase):
    pass

class Internal_ProductRead(Internal_ProductBase):
    pass

class Internal_ProductUpdate(Internal_ProductBase):
    pass
