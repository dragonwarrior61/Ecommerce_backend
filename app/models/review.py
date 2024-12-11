from sqlalchemy import Column, Integer, Text, PrimaryKeyConstraint
from app.database import Base

class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, autoincrement=True)  # Ensure id is a primary key and auto-incrementing
    product_id = Column(Text, nullable=True)
    ean = Column(Text, nullable=True)
    review_id = Column(Integer, nullable=False)  # Removed primary_key=True
    user_id = Column(Integer, nullable=True)
    user_name = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    moderated_by = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)
    brand_id = Column(Integer, nullable=True)
    admin_id = Column(Integer, nullable=True)
    review_marketplace = Column(Text, nullable=True)   

    __table_args__ = (
        PrimaryKeyConstraint('id', 'review_marketplace', 'review_id', name='pk_review_id_review_marketplace'),  # Updated composite primary key
    )