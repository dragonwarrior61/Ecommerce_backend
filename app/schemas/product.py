from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal

class ProductBase(BaseModel):
    id: Optional[str] = None
    part_number_key: Optional[str] = None
    product_name: Optional[str] = None
    model_name: Optional[str] = None
    buy_button_rank: Optional[int] = None
    price: Optional[Decimal] = None
    sale_price: Optional[Decimal] = None
    sku: Optional[str] = None
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
    warehouse_id: Optional[int] = None
    internal_shipping_price: Optional[Decimal] = None
    observation: Optional[str] = None
    product_marketplace: str
    user_id: Optional[int] = None

class ProductCreate(ProductBase):
    pass

class ProductRead(ProductBase):
    pass

class ProductUpdate(ProductBase):
    pass
