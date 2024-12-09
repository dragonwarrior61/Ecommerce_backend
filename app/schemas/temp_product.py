from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal

class Temp_productBase(BaseModel):
    product_name: Optional[str] = None
    model_name: Optional[str] = None
    price: Optional[Decimal] = None
    image_link: Optional[str] = None
    barcode_title: Optional[str] = None
    masterbox_title: Optional[str] = None
    pcs_ctn: Optional[str] = None
    weight: Optional[Decimal] = None
    supplier_id: Optional[int] = None
    english_name: Optional[str] = None
    romanian_name: Optional[str] = None
    material_name_en: Optional[str] = None
    material_name_ro: Optional[str] = None
    hs_code: Optional[str] = None
    battery: Optional[bool] = None
    default_usage: Optional[str] = None
    smartbill_stock: Optional[int] = None
    internal_shipping_price: Optional[Decimal] = None
    user_id: Optional[int] = None

class Temp_productCreate(Temp_productBase):
    pass

class Temp_productRead(Temp_productBase):
    id: int

    class Config:
        orm_mode = True

class Temp_productUpdate(Temp_productBase):
    pass
