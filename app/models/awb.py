# app/models/awb.py
from sqlalchemy import Column, Integer, String, BigInteger, DECIMAL, PrimaryKeyConstraint, DateTime
from sqlalchemy.orm import relationship
from app.database import Base


class AWB(Base):
    __tablename__ = "awbs"
    
    order_id = Column(Integer, nullable=True)
    number = Column(Integer, default_value=0)
    sender_name = Column(String, nullable=True)
    sender_phone1 = Column(String, nullable=True)
    sender_phone2 = Column(String, nullable=True)
    sender_locality_id = Column(BigInteger, nullable=True)
    sender_street = Column(String, nullable=True)
    sender_zipcode = Column(String, nullable=True)
    receiver_name = Column(String, nullable=True)
    receiver_contact = Column(String, nullable=True)
    receiver_phone1 = Column(String, nullable=True)
    receiver_phone2 = Column(String, nullable=True)
    receiver_legal_entity = Column(Integer, nullable=True)
    receiver_locality_id = Column(BigInteger, nullable=True)
    receiver_street = Column(String, nullable=True)
    receiver_zipcode = Column(String, nullable=True)
    locker_id = Column(String, nullable=True)
    is_oversize = Column(Integer, nullable=True)
    insured_value = Column(DECIMAL, nullable=True) 
    weight = Column(DECIMAL, nullable=True)
    envelope_number = Column(Integer, nullable=False)
    parcel_number = Column(Integer, nullable=True)
    observation = Column(String, nullable=True)
    cod = Column(DECIMAL, nullable=True)
    courier_account_id = Column(Integer, nullable=True)
    pickup_and_return = Column(Integer, nullable=True)
    saturday_delivery = Column(Integer, nullable=True)
    sameday_delivery = Column(Integer, nullable=True)
    dropoff_locker = Column(Integer, nullable=True)
    reservation_id = Column(Integer, nullable=True)
    courier_id = Column(Integer, nullable=True)
    courier_name = Column(String, nullable=True)
    awb_number = Column(String, nullable=True, index=True)
    awb_barcode = Column(String, nullable=True)
    awb_marketplace = Column(String, nullable=True)
    status = Column(Integer, default_value=0)
    awb_date = Column(DateTime, nullable=True)

    __table_args__ = (
        PrimaryKeyConstraint('order_id', 'number', name='pk_order_id_number'),
    )