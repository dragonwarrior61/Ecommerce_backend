from sqlalchemy import Column, Integer, Text
from app.database import Base

class Billing_software(Base):
    __tablename__ = "billing_softwares"
    id = Column(Integer, primary_key=True, autoincrement=True)  # Ensure id is a primary key and auto-incrementing
    user_id = Column(Integer, nullable=True)
    site_domain = Column(Text, nullable=True)
    company_name = Column(Text, nullable=True)
    username = Column(Text, nullable=True)
    password = Column(Text, nullable=True)
    registration_number = Column(Text, nullable=True)
    warehouse_name = Column(Text, nullable=True)
    

