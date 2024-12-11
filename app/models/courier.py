from sqlalchemy import Column, Integer, String, PrimaryKeyConstraint, BigInteger, DateTime, ARRAY
from app.database import Base


class Courier(Base):
    __tablename__ = 'couriers'
    account_id = Column(Integer, primary_key=True)
    account_display_name = Column(String, nullable=True)
    courier_account_type = Column(Integer, nullable=True)
    courier_name = Column(String, nullable=True)
    courier_account_properties = Column(String, nullable=True)
    created = Column(DateTime, nullable=True)
    status = Column(Integer, nullable=True)
    market_place = Column(String, nullable=True)
    user_id = Column(Integer, nullable=True)
    __table_args__ = (
        PrimaryKeyConstraint('account_id', 'market_place', name='pk_account_id_market_place'),
    )

