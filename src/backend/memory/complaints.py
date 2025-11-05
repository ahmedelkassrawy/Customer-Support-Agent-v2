from .base import Base
from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.orm import relationship

class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(String, primary_key=True, index=True, unique=True)
    order_id = Column(String, ForeignKey("orders.order_id"), index=True)
    issue = Column(Text)
    escalation_status = Column(String, default="Not Escalated")

    # Relationship to Order
    order = relationship("Order", back_populates="complaints")
    
    # Relationship to Escalations (one complaint can have multiple escalations)
    escalations = relationship("Escalation", back_populates="complaint", cascade="all, delete-orphan")
