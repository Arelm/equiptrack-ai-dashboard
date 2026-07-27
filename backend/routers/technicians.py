from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from routers.auth import get_current_user
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
def get_technicians(
    organizationId: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Returns the roster the assign picker draws on.

    passwordHash is never serialised. canLogIn is exposed instead, because a
    technician who cannot authenticate cannot accept a job, and assigning work
    to him looks identical to assigning work to someone who can.
    """
    if organizationId != user.get("orgId"):
        raise HTTPException(status_code=403, detail="Wrong organisation")
    rows = db.query(User).filter(User.organizationId == organizationId).all()
    return [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role.value if hasattr(u.role, "value") else u.role,
            "isActive": u.isActive is not False,
            "canLogIn": bool(u.passwordHash),
        }
        for u in rows
    ]

@router.post("/")
def create_technician(tech: TechnicianCreate, db: Session = Depends(get_db)):
    db_tech = User(id=str(uuid.uuid4()), **tech.model_dump())
    db.add(db_tech)
    db.commit()
    db.refresh(db_tech)
    return db_tech