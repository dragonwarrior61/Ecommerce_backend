from sqlalchemy import Column, Integer, String, DateTime, PrimaryKeyConstraint
from app.database import Base

class Locality(Base):
    __tablename__ = 'localities'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    name_latin = Column(String, nullable=True)
    region1 = Column(String, nullable=True)
    region1_latin = Column(String, nullable=True)
    region2 = Column(String, nullable=True)
    region2_latin = Column(String, nullable=True)
    region3 = Column(String, nullable=True)
    region3_latin = Column(String, nullable=True)
    geoid = Column(Integer, nullable=True)
    modified = Column(DateTime, nullable=True)
    zipcode = Column(String, nullable=True)
    country_code = Column(String, nullable=True)
    localtity_marketplace = Column(String, nullable=True)
    user_id = Column(Integer, nullable=True)

    __table_args__ = (
        PrimaryKeyConstraint('id', 'localtity_marketplace', name='pk_id_localtity_marketplace'),
    )