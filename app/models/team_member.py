from sqlalchemy import Column, Integer, ARRAY
from app.database import Base
from datetime import datetime
class Team_member(Base):
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True)
    admin = Column(Integer, index=True, nullable=True)
    user = Column(Integer, nullable=True)
    