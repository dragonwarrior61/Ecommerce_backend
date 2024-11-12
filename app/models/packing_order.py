from sqlalchemy import Column, Integer, Text, DateTime, ARRAY, Numeric, Boolean
from app.database import Base

class Packing_order(Base):
    __tablename__ = "packing_orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    awb_number = Column(Text, nullable=True, index=True)
    order_id = Column(Integer, nullable=True, index=True)
    product_ean = Column(ARRAY(Text), nullable=True)
    quantity = Column(ARRAY(Integer), nullable=True)
    order_quantity = Column(ARRAY(Integer), nullable=True)
    staff_id = Column(Integer, nullable=True)
    pack_status = Column(Integer, nullable=True)
    starting_time = Column(DateTime, nullable=True)
    ending_time = Column(DateTime, nullable=True)
    user_id = Column(Integer, index=True, nullable=True)