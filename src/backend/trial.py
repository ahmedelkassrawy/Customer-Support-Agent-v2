from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
from uuid import uuid4
from sqlalchemy.orm import Session
from config import get_settings
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from memory.base import Base, engine
from memory.complaints import Complaint
from memory.escalation import Escalation
from memory.order import Order 
from sqlalchemy.orm import sessionmaker
import uvicorn

Base.metadata.create_all(bind=engine)
settings = get_settings()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(title = "Customer Service API")

class ComplaintCreate(BaseModel):
    id:str
    order_id:str
    issue:str

class ComplaintResponse(BaseModel):
    message:str
    complaint_id:str

class EscalationRequest(BaseModel):
    complaint_id:str
    reason:Optional[str] = "Urgent attention required"

class EscalationResponse(BaseModel):
    message:str
    escalation_id:str

@app.post("/complaints/",response_model = ComplaintResponse)
def create_complaint(complaint:ComplaintCreate,
                     db:Session = Depends(get_db)):
    """Create a new complaint"""
    existing = db.query(Complaint).filter(Complaint.id == complaint.id).first()

    if existing:
        raise HTTPException(status_code = 400,
                            detail = "Complaint with this ID already exists.")

    order = db.query(Order).filter(Order.order_id == complaint.order_id).first()

    if not order:
        raise HTTPException(status_code = 404,
                            detail = "Order doesn't exist")

    new_complaint = Complaint(id = complaint.id,
                              order_id = complaint.order_id,
                              issue = complaint.issue,
                              escalation_status = "Not Escalated")
    db.add(new_complaint)
    db.commit()
    db.refresh(new_complaint)

@app.get("/orders/{order_id}")
def get_order_status(order_id:str,
                     db:Session = Depends(get_db)):
    """Get order status by order ID"""
    order = db.query(Order).filter(Order.order_id == order_id).first()

    if not order:
        raise HTTPException(status_code = 404,
                            detail = "Order not found")

    return {"order_id": order.order_id,
            "status": order.status,
            "estimated_delivery": order.estimated_delivery}

@app.post("/escalations/",response_model = EscalationResponse)
def escalate_complaint(escalation:EscalationRequest,
                       db:Session = Depends(get_db)):   
    """Escalate an existing complaint"""
    complaint = db.query(Complaint).filter(
        Complaint.id == escalation.complaint_id
    ).first()

    if not complaint:
        raise HTTPException(status_code = 404,
                            detail = "Complaint not found")

    escalation_id = str(uuid4())
    new_escalation = Escalation(
        id = escalation_id,
        complaint_id = escalation.complaint_id,
        escalation_status = "Escalated"
    )
    complaint.escalation_status = "Escalated"

    db.add(new_escalation)
    db.commit()
    db.refresh(new_escalation)

    return EscalationResponse(
        message = "Complaint escalated successfully",
        escalation_id = new_escalation.id)

@app.get("/complaints/{complaint_id}")
def get_complaint(complaint_id: str, db: Session = Depends(get_db)):
    """Get complaint details by ID"""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    
    return {
        "id": complaint.id,
        "order_id": complaint.order_id,
        "issue": complaint.issue,
        "escalation_status": complaint.escalation_status
    }