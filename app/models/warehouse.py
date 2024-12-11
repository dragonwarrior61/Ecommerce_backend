from sqlalchemy import Column, Integer, Text, Boolean
from app.database import Base

class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(Text, nullable=True)
    sender_name = Column(Text, nullable=True)
    sender_contact = Column(Text, nullable=True)
    phone1 = Column(Text, nullable=True)
    phone2 = Column(Text, nullable=True)
    legal_entity = Column(Boolean, nullable=True)
    locality_id = Column(Text, nullable=True)
    street = Column(Text, nullable=True)
    zipcode = Column(Text, nullable=True)
    user_id = Column(Integer, nullable=True)
    