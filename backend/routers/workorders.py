from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import WorkOrder, WorkOrderStatusEnum, PriorityEnum
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

router = APIRouter()

class WorkOrderCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: PriorityEnum = PriorityEnum.MEDIUM
    organizationId: str
    assetId: Optional[str] = None
    locationId: Optional[str] = None
    dueDate: Optional[datetime] = None

class WorkOrderUpdate(BaseModel):
    status: Optional[WorkOrderStatusEnum] = None
    priority: Optional[PriorityEnum] = None
    description: Optional[str] = None
    completedAt: Optional[datetime] = None

@router.get("/")
def get_workorders(organizationId: str, db: Session = Depends(get_db)):
    return db.query(WorkOrder).filter(WorkOrder.organizationId == organizationId).all()

@router.get("/{wo_id}")
def get_workorder(wo_id: str, db: Session = Depends(get_db)):
    wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")
    return wo

@router.post("/")
def create_workorder(wo: WorkOrderCreate, db: Session = Depends(get_db)):
    now = datetime.utcnow()
    db_wo = WorkOrder(
        id=str(uuid.uuid4()),
        createdAt=now,
        updatedAt=now,
        **wo.model_dump(),
    )
    db.add(db_wo)
    db.commit()
    db.refresh(db_wo)
    return db_wo

@router.patch("/{wo_id}")
def update_workorder(wo_id: str, update: WorkOrderUpdate, db: Session = Depends(get_db)):
    wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")
    for key, value in update.model_dump(exclude_none=True).items():
        setattr(wo, key, value)
    wo.updatedAt = datetime.utcnow()
    db.commit()
    db.refresh(wo)
    return wo

@router.delete("/{wo_id}")
def delete_workorder(wo_id: str, db: Session = Depends(get_db)):
    wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")
    db.delete(wo)
    db.commit()
    return {"message": "Work order deleted"}