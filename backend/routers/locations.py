"""
Client sites.

A location is not a JDAEM site. It is a client site: a Sterling Oil
plot on the Island, identified by its plot number (217B, OML13A),
sitting in an area (V.I., Ikeja, Elegushi), with a site supervisor who
works for the client under a labour contractor.

The supervisor is a contact, not a user. A technician sent to a plot
needs a name and a number to call on arrival, nothing more. No login
is created for them and they get no row in "User".

Retired plots are deactivated rather than deleted, so the work orders
raised against them keep their history.

Reads are open to any signed-in user, because a technician needs to
see the site they are dispatched to. Writes are manager and admin
only, matching parts and assignments.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from database import get_db
from models import Location, RoleEnum
from routers.auth import get_current_user, require_role

router = APIRouter()

MANAGER = (RoleEnum.MANAGER.value, RoleEnum.ADMIN.value)


def _clean(value: Optional[str]) -> Optional[str]:
    """Trim whitespace and treat a blank string as absent."""
    if value is None:
        return None
    value = value.strip()
    return value or None


class LocationCreate(BaseModel):
    name: str
    organizationId: str
    client: Optional[str] = None
    supervisorName: Optional[str] = None
    supervisorPhone: Optional[str] = None
    area: Optional[str] = None
    address: Optional[str] = None
    isActive: bool = True

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Location name is required")
        return v

    @field_validator(
        "client", "supervisorName", "supervisorPhone", "area", "address"
    )
    @classmethod
    def tidy(cls, v: Optional[str]) -> Optional[str]:
        return _clean(v)


class LocationUpdate(BaseModel):
    """Every field optional: send only what changed."""

    name: Optional[str] = None
    client: Optional[str] = None
    supervisorName: Optional[str] = None
    supervisorPhone: Optional[str] = None
    area: Optional[str] = None
    address: Optional[str] = None
    isActive: Optional[bool] = None

    @field_validator(
        "name", "client", "supervisorName", "supervisorPhone", "area", "address"
    )
    @classmethod
    def tidy(cls, v: Optional[str]) -> Optional[str]:
        return _clean(v)


@router.get("/")
def get_locations(
    organizationId: str,
    includeInactive: bool = False,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Active sites by default. Dropdowns should never offer a dead plot."""
    query = db.query(Location).filter(Location.organizationId == organizationId)
    if not includeInactive:
        query = query.filter(Location.isActive.is_(True))
    return query.order_by(Location.name).all()


@router.get("/{location_id}")
def get_location(
    location_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    return location


@router.post("/")
def create_location(
    location: LocationCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(*MANAGER)),
):
    # Plot numbers are the whole point of the name. Two sites called
    # 217B in one organization means a dispatch goes to the wrong gate.
    existing = (
        db.query(Location)
        .filter(
            Location.organizationId == location.organizationId,
            Location.name.ilike(location.name),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"A location named '{location.name}' already exists",
        )

    db_location = Location(id=str(uuid.uuid4()), **location.model_dump())
    db.add(db_location)
    db.commit()
    db.refresh(db_location)
    return db_location


@router.patch("/{location_id}")
def update_location(
    location_id: str,
    changes: LocationUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(*MANAGER)),
):
    """Used to correct a supervisor, or to retire a plot by setting
    isActive false when the client hands it back."""
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    updates = changes.model_dump(exclude_unset=True)

    if "name" in updates:
        if not updates["name"]:
            raise HTTPException(status_code=422, detail="Location name is required")
        clash = (
            db.query(Location)
            .filter(
                Location.organizationId == location.organizationId,
                Location.name.ilike(updates["name"]),
                Location.id != location_id,
            )
            .first()
        )
        if clash:
            raise HTTPException(
                status_code=409,
                detail=f"A location named '{updates['name']}' already exists",
            )

    for field, value in updates.items():
        setattr(location, field, value)

    db.commit()
    db.refresh(location)
    return location
