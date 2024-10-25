from pydantic import BaseModel
from typing import Optional

class ReviewBase(BaseModel):

    product_id: Optional[str] = None
    ean: Optional[str] = None
    review_id: Optional[int] = None
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    content: Optional[str] = None
    moderated_by: Optional[str] = None
    rating: Optional[int] = None
    brand_id: Optional[int] = None
    review_marketplace: Optional[str] = None
    admin_id = Optional[int] = None
class ReviewCreate(ReviewBase):
    pass

class ReviewRead(ReviewBase):
    id: int
    review_id: int
    review_marketplace:str

    class Config:
        orm_mode = True
class ReviewUpdate(ReviewBase):
    pass