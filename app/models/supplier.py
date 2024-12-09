from sqlalchemy import Column, Integer, Text
from app.database import Base

class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    group = Column(Text, nullable=True)
    name = Column(Text, nullable=True)
    wechat = Column(Text, nullable=True)
    user_id = Column(Integer, nullable=True)
    