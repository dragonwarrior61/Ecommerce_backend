from sqlalchemy import Column, Integer, Text, PrimaryKeyConstraint, Boolean, DateTime
from app.database import Base

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer)
    title = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    time = Column(DateTime, nullable=True)
    ean = Column(Text, nullable=False)
    state = Column(Text, nullable=False)
    read = Column(Boolean, nullable=False)
    user_id = Column(Integer, index=True, nullable=False)
    market_place = Column(Text, nullable=True)

    __table_args__ = (
        PrimaryKeyConstraint('title', 'ean', 'market_place', name='pk_notifi_ean_market_place'),
    )