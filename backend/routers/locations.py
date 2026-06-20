from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Location
from pydantic import BaseModel
from typing import Optional
import uuid

router = APIRouter()

class LocationCreate(BaseModel):
    name: str
    address: Optional[str] = None
    organizationId: str

@router.get("/")
def get_locations(organizationId: str, db: Session = Depends(get_db)):
    return db.query(Location).filter(Location.organizationId == organizationId).all()

@router.get("/{location_id}")
def get_location(location_id: str, db: Session = Depends(get_db)):
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location

@router.post("/")
def create_location(location: LocationCreate, db: Session = Depends(get_db)):
    db_location = Location(id=str(uuid.uuid4()), **location.model_dump())
    db.add(db_location)
    db.commit()
    db.refresh(db_location)
    return db_location