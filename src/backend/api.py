from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select
import sys
from pathlib import Path

# Add root directory to path so we can import config
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from config import get_settings

# Add parent directory to path for local imports
sys.path.insert(0, str(Path(__file__).parent))

from memory.base import Base, async_engine, sync_engine
from memory.complaints import Complaint 
from memory.order import Order 
from memory.escalation import Escalation 
import uvicorn

# Create tables using sync engine
Base.metadata.create_all(bind=sync_engine)
settings = get_settings()

# Create async session maker
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

app = FastAPI(title="Customer Service API")

class ComplaintCreate(BaseModel):
    id: str
    order_id: str
    issue: str

class ComplaintResponse(BaseModel):
    message: str
    complaint_id: str

class EscalationRequest(BaseModel):
    complaint_id: str

class EscalationResponse(BaseModel):
    message: str
    escalation_id: str

# Initialize sample orders if database is empty
async def init_sample_data(db: AsyncSession):
    """Initialize sample orders if they don't exist"""
    sample_orders = [
        {"order_id": "ORD123", "status": "Shipped", "estimated_delivery": "2025-07-20"},
        {"order_id": "ORD456", "status": "Processing", "estimated_delivery": "2025-07-25"},
        {"order_id": "ORD141", "status": "Delivered", "estimated_delivery": "2025-07-15"}
    ]
    
    for order_data in sample_orders:
        result = await db.execute(select(Order).filter(Order.order_id == order_data["order_id"]))
        existing = result.scalar_one_or_none()
        if not existing:
            order = Order(**order_data)
            db.add(order)
    
    await db.commit()

# Initialize on startup
@app.on_event("startup")
async def startup_event():
    async with AsyncSessionLocal() as db:
        await init_sample_data(db)

@app.post("/complaints", response_model=ComplaintResponse)
async def create_complaint(complaint: ComplaintCreate, db: AsyncSession = Depends(get_db)):
    """Create a new complaint"""
    result = await db.execute(select(Complaint).filter(Complaint.id == complaint.id))
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=400, detail="Complaint already exists")
    
    result = await db.execute(select(Order).filter(Order.order_id == complaint.order_id))
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    db_complaint = Complaint(
        id=complaint.id,
        order_id=complaint.order_id,
        issue=complaint.issue,
        escalation_status="Not Escalated"
    )
    
    db.add(db_complaint)
    await db.commit()
    await db.refresh(db_complaint)
    
    return ComplaintResponse(
        message="Complaint created successfully",
        complaint_id=db_complaint.id
    )

@app.get("/orders/{order_id}")
async def get_order_status(order_id: str, db: AsyncSession = Depends(get_db)):
    """Get order status by order ID"""
    result = await db.execute(select(Order).filter(Order.order_id == order_id))
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {
        "order_id": order.order_id,
        "status": order.status,
        "estimated_delivery": order.estimated_delivery
    }

@app.post("/escalations", response_model=EscalationResponse)
async def escalate_complaint(escalation: EscalationRequest, db: AsyncSession = Depends(get_db)):
    """Escalate an existing complaint"""
    # Check if complaint exists
    result = await db.execute(select(Complaint).filter(Complaint.id == escalation.complaint_id))
    complaint = result.scalar_one_or_none()
    
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    
    escalation_id = str(uuid4())
    
    new_escalation = Escalation(
        id=escalation_id,
        complaint_id=escalation.complaint_id,
        status="Pending"
    )
    
    # Update complaint escalation status
    complaint.escalation_status = "Escalated"
    
    db.add(new_escalation)
    await db.commit()
    await db.refresh(new_escalation)
    
    return EscalationResponse(
        message="Complaint escalated successfully",
        escalation_id=new_escalation.id
    )

@app.get("/complaints/{complaint_id}")
async def get_complaint(complaint_id: str, db: AsyncSession = Depends(get_db)):
    """Get complaint details by ID"""
    result = await db.execute(select(Complaint).filter(Complaint.id == complaint_id))
    complaint = result.scalar_one_or_none()
    
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    
    return {
        "id": complaint.id,
        "order_id": complaint.order_id,
        "issue": complaint.issue,
        "escalation_status": complaint.escalation_status
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

@app.get("/complaints/check_by_order/{order_id}")
async def check_complaint_by_order(order_id: str, db: AsyncSession = Depends(get_db)):
    """Check if a complaint exists for a given order ID"""
    result = await db.execute(select(Complaint).filter(Complaint.order_id == order_id))
    complaint = result.scalar_one_or_none()

    if complaint:
        return {
            "exists": True,
            "complaint_id": complaint.id,
            "issue": complaint.issue,
            "escalation_status": complaint.escalation_status
        } 
    else:
        return {
            "exists": False
        }

@app.get("/complaints/check_by_id/{complaint_id}")
async def check_complaint_by_id(complaint_id: str, db: AsyncSession = Depends(get_db)):
    """Check if a complaint exists for a given complaint ID"""
    result = await db.execute(select(Complaint).filter(Complaint.id == complaint_id))
    complaint = result.scalar_one_or_none()

    if complaint:
        return {
            "exists": True,
            "complaint_id": complaint.id,
            "issue": complaint.issue,
            "escalation_status": complaint.escalation_status
        } 
    else:
        return {
            "exists": False
        }