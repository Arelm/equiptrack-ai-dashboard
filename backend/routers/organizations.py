from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Organization

router = APIRouter()

@router.get("/")
def get_organizations(db: Session = Depends(get_db)):
    return db.query(Organization).all()

@router.get("/{org_id}")
def get_organization(org_id: str, db: Session = Depends(get_db)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org