from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import User, RoleEnum
from pydantic import BaseModel
from typing import Optional
import uuid

router = APIRouter()

class TechnicianCreate(BaseModel):
    email: str
    name: str
    role: RoleEnum = RoleEnum.TECHNICIAN
    organizationId: str

@router.get("/")
def get_technicians(organizationId: str, db: Session = Depends(get_db)):
    return db.query(User).filter(User.organizationId == organizationId).all()

@router.post("/")
def create_technician(tech: TechnicianCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == tech.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    db_user = User(id=str(uuid.uuid4()), **tech.model_dump())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user