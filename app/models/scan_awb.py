from sqlalchemy import Column, Integer, String, PrimaryKeyConstraint, DateTime
from app.database import Base


class Scan_awb(Base):
    __tablename__ = 'scan_awbs'
    id = Column(Integer, primary_key=True)
    awb_number = Column(String, nullable=True, index=True)
    awb_type = Column(String, nullable=True)
    scan_date = Column(DateTime, nullable=True)
    user_id = Column(Integer, nullable=True)


