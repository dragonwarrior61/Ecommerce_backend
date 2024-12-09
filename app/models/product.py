from sqlalchemy import Column, Integer, String, Text, Numeric, Boolean, PrimaryKeyConstraint
from app.database import Base

class Product(Base):
    __tablename__ = "products"
    id = Column(String, nullable=True, index=True)
    part_number_key = Column(String, nullable=True)
    product_name = Column(Text, nullable=True)
    model_name = Column(Text, nullable=True)
    buy_button_rank = Column(Integer, nullable=True)
    sku = Column(Text, nullable=True)
    ean = Column(Text, nullable=True)
    price = Column(Numeric(12, 4), nullable=True)
    sale_price = Column(Numeric(12, 4), nullable=True)
    image_link = Column(Text, nullable=True)
    barcode_title = Column(Text, nullable=True)
    masterbox_title = Column(Text, nullable=True)
    link_address_1688 = Column(Text, nullable=True)
    price_1688 = Column(Numeric(12, 4), nullable=True)
    variation_name_1688 = Column(Text, nullable=True)
    pcs_ctn = Column(Text, nullable=True)
    weight = Column(Numeric(12, 4), nullable=True)
    volumetric_weight = Column(Numeric(12, 4), nullable=True)
    dimensions = Column(Text, nullable=True)
    supplier_id = Column(Integer, nullable=True)
    english_name = Column(Text, nullable=True)
    romanian_name = Column(Text, nullable=True)
    material_name_en = Column(Text, nullable=True)
    material_name_ro = Column(Text, nullable=True)
    hs_code = Column(Text, nullable=True)
    battery = Column(Boolean, nullable=True)
    default_usage = Column(Text, nullable=True)
    production_time = Column(Numeric(12, 4), nullable=True)
    discontinued = Column(Boolean, nullable=True)
    stock = Column(Integer, nullable=True)
    warehouse_id = Column(Integer, nullable=True)
    internal_shipping_price = Column(Numeric(12, 4), nullable=True)
    observation = Column(Text, nullable=True)
    product_marketplace = Column(Text, nullable=True)
    user_id = Column(Integer, index=True, nullable=True)
    
    __table_args__ = (
        PrimaryKeyConstraint('ean', 'product_marketplace', name='pk_ean_product_marketplace'),
    )