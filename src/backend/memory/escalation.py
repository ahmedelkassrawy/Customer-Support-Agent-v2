from .base import Base
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship

class Escalation(Base):
    __tablename__ = "escalations"

    id = Column(String, primary_key=True, index=True, unique=True)
    complaint_id = Column(String, ForeignKey("complaints.id"), nullable=False, index=True)
    status = Column(String, default="Pending")

    # Relationship to Complaint
    complaint = relationship("Complaint", back_populates="escalations")
