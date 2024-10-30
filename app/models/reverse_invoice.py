from sqlalchemy import Column, Integer, Text, DateTime, ARRAY, Numeric, Boolean
from app.database import Base

class Reverse_Invoice(Base):
    __tablename__ = "reverse_invoices"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    replacement_id = Column(Integer, nullable=True, index=True)
    order_id = Column(Integer, nullable=True, index=True)
    companyVatCode = Column(Text, nullable=True)
    seriesName = Column(Text, nullable=True)
    factura_number = Column(Text, nullable=True, index=True)
    storno_number = Column(Text, nullable=True, index=True)
    post = Column(Integer, nullable=True)
    user_id = Column(Integer, index=True, nullable=True)

    