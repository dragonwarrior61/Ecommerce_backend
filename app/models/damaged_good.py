from sqlalchemy import Column, Integer, Text, DateTime, ARRAY, Numeric, Boolean
from app.database import Base

class Damaged_good(Base):
    __tablename__ = "damaged_goods"

    id = Column(Integer, primary_key=True, autoincrement=True)
    return_id = Column(Integer, index=True, nullable=True)
    return_reason = Column(Text, nullable=True)
    return_date = Column(DateTime, nullable=True)
    product_ean = Column(ARRAY(Text), nullable=True)
    product_id = Column(ARRAY(Integer), nullable=True)
    product_code = Column(ARRAY(Text), nullable=True)
    quantity = Column(ARRAY(Integer), nullable=True)
    awb = Column(Text, nullable=True)
    user_id = Column(Integer, nullable=True)

    