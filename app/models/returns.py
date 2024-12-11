from sqlalchemy import Column, Integer, String, PrimaryKeyConstraint, BigInteger, ARRAY, DateTime
from app.database import Base

class Returns(Base):
    __tablename__ = "returns"
    emag_id = Column(BigInteger, nullable=True)
    order_id = Column(BigInteger, index=True)
    type = Column(Integer, nullable=True)
    customer_name = Column(String, nullable=True)
    customer_company = Column(String, nullable=True)
    customer_phone = Column(String, nullable=True)
    products = Column(ARRAY(String), nullable=True)
    quantity = Column(ARRAY(Integer), nullable=True)
    observations = Column(ARRAY(String), nullable=True)
    pickup_address = Column(String, nullable=True)
    return_reason = Column(String, nullable=True)
    return_type = Column(Integer, nullable=True)
    replacement_product_emag_id = Column(Integer, nullable=True)
    replacement_product_id = Column(Integer, nullable=True)
    replacement_product_name = Column(String, nullable=True)
    replacement_product_quantity = Column(Integer, nullable=True)
    date = Column(DateTime, nullable=True)
    request_status = Column(Integer, nullable=True)
    return_market_place = Column(String, nullable=True)
    awb = Column(String, nullable=True)
    awb_status = Column(String, nullable=True)
    user_id = Column(Integer, index=True, nullable=True)

    __table_args__ = (
        PrimaryKeyConstraint('emag_id', 'return_market_place', name='pk_emag_id_return_market_place'),
    )