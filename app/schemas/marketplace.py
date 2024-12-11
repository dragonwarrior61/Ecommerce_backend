from pydantic import BaseModel, HttpUrl, EmailStr
from typing import Dict
from typing import Optional

class Credentials(BaseModel):
    type: Optional[str] = None
    firstKey: Optional[str] = None
    secondKey: Optional[str] = None

class CRUDOperations(BaseModel):
    endpoint: Optional[str] = None
    create: Optional[str] = None
    read: Optional[str] = None
    update: Optional[str] = None
    delete: Optional[str] = None
    count: Optional[str] = None

class MarketplaceBase(BaseModel):
    title: Optional[str] = None
    baseURL: Optional[str] = None
    marketplaceDomain: Optional[str] = None
    country: Optional[str] = None
    baseAPIURL: Optional[str] = None
    credentials: Optional[Credentials] = None
    image_url: Optional[str] = None
    vat: Optional[int] = None
    user_id: Optional[int] = None
    proxy: Optional[str] = None
    products_crud: CRUDOperations = CRUDOperations(
        endpoint="/product_offer",
        create="/create",
        read="/read",
        update="/update",
        delete="/delete",
        count="/count"
    )
    orders_crud: CRUDOperations = CRUDOperations(
        endpoint="/order",
        create="/create",
        read="/read",
        update="/update",
        delete="/delete",
        count="/count"
    )
    
class MarketplaceCreate(MarketplaceBase):
    pass

class MarketplaceUpdate(MarketplaceBase):
    pass

class MarketplaceRead(MarketplaceBase):
    id: int

    class Config:
        orm_mode = True
