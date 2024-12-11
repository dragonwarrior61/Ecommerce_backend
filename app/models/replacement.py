from sqlalchemy import Column, Integer, Text, DateTime, ARRAY, Numeric, Boolean
from app.database import Base

class Replacement(Base):
    __tablename__ = "replacements"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_id = Column(Integer, nullable=True)
    number = Column(Integer, nullable=True, default=1)
    date = Column(DateTime, nullable=True)
    product_ean = Column(ARRAY(Text), nullable=True)
    quantity = Column(ARRAY(Integer), nullable=True)
    price = Column(ARRAY(Numeric(12, 4)), nullable=True)
    marketplace = Column(Text, nullable=True)
    reason = Column(Text, nullable=True)
    awb = Column(Text, nullable=True)
    total = Column(Numeric(12,4), nullable=True)
    status = Column(Integer, nullable=True)
    customer_name = Column(Text, nullable=True)
    customer_address = Column(Text, nullable=True)
    customer_email = Column(Text, nullable=True)
    customer_phone = Column(Text, nullable=True)
    review = Column(Boolean, nullable=True)
    review_content = Column(Text, nullable=True)
    customer_comment = Column(Text, nullable=True)
    user_id = Column(Integer, index=True, nullable=True)


    