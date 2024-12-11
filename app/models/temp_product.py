from sqlalchemy import Column, Integer, String, Text, Numeric, Boolean, ARRAY, BigInteger
from app.database import Base
from sqlalchemy.orm import relationship

class Temp_product(Base):
    __tablename__ = "temp_products"

    id = Column(Integer, primary_key=True)
    product_name = Column(Text, nullable=True)
    model_name = Column(Text, nullable=True)
    price = Column(Numeric(12, 4), nullable=True)
    image_link = Column(Text, nullable=True)
    barcode_title = Column(Text, nullable=True)
    masterbox_title = Column(Text, nullable=True)
    pcs_ctn = Column(Text, nullable=True)
    weight = Column(Numeric(12, 6), nullable=True)
    supplier_id = Column(Integer, nullable=True)
    english_name = Column(Text, nullable=True)
    romanian_name = Column(Text, nullable=True)
    material_name_en = Column(Text, nullable=True)
    material_name_ro = Column(Text, nullable=True)
    hs_code = Column(Text, nullable=True)
    battery = Column(Boolean, nullable=True)
    default_usage = Column(Text, nullable=True)
    smartbill_stock = Column(Integer, nullable=True)
    internal_shipping_price = Column(Numeric(12, 6), nullable=True)
    user_id = Column(Integer, nullable=True)