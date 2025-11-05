from .base import Base
from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

class Order(Base):
    __tablename__ = "orders"

    order_id = Column(String, primary_key=True, unique=True, index=True)
    status = Column(String, nullable=False)
    estimated_delivery = Column(String, nullable=False)

    # Relationship to Complaint
    complaints = relationship("Complaint", back_populates="order")