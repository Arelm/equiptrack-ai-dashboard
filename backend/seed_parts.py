"""Parts catalogue and stock ledger.

The technician app read its parts list from lib/data.ts, a static mock. These are
the endpoints that replace it with the PartsInventory table that already existed
and was never exposed.

Quantities are decimal because refrigerant is charged in fractions of a kilo and
copper is cut to fractions of a metre. Every part carries a unit, because
"quantity 5" means nothing on its own — five metres of pipe, five pieces of
Armaflex and five kilos of R-32 are different declarations.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from database import get_db
from models import (
    PartsInventory,
    RoleEnum,
    StockMovement,
    StockReasonEnum,
    User,
)
from routers.auth import get_current_user, require_role
from services.stock import record_movement, reconcile

router = APIRouter()

VALID_UNITS = ["pcs", "m", "kg", "length", "set", "litre"]

MANAGER = (RoleEnum.MANAGER.value, RoleEnum.ADMIN.value)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _serialise(p: PartsInventory) -> dict:
    qty = float(p.quantity or 0)
    reorder = float(p.reorderLevel or 0)
    return {
        "id": p.id,
        "name": p.name,
        "partNumber": p.partNumber,
        "quantity": qty,
        "reorderLevel": reorder,
        "unit": p.unit or "pcs",
        "category": p.category,
        "lowStock": qty <= reorder,
    }


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

@router.get("/")
def list_parts(organizationId: str, db: Session = Depends(get_db),
               user: dict = Depends(get_current_user)):
    if organizationId != user.get("orgId"):
        raise HTTPException(status_code=403, detail="Wrong organisation")
    parts = (
        db.query(PartsInventory)
        .filter(PartsInventory.organizationId == organizationId)
        .order_by(PartsInventory.category.asc(), PartsInventory.name.asc())
        .all()
    )
    return [_serialise(p) for p in parts]


@router.get("/low-stock")
def low_stock(organizationId: str, db: Session = Depends(get_db),
              user: dict = Depends(get_current_user)):
    """The dashboard's "Parts low stock" counter, now backed by a moving number."""
    if organizationId != user.get("orgId"):
        raise HTTPException(status_code=403, detail="Wrong organisation")
    parts = db.query(PartsInventory).filter(
        PartsInventory.organizationId == organizationId,
        PartsInventory.quantity <= PartsInventory.reorderLevel,
    ).all()
    return {"count": len(parts), "parts": [_serialise(p) for p in parts]}


@router.get("/reconcile")
def run_reconcile(db: Session = Depends(get_db),
                  user: dict = Depends(require_role(RoleEnum.ADMIN.value))):
    """Cached balance vs ledger. A non-empty result is a bug, not a report."""
    drift = reconcile(db)
    return {"drift": drift, "clean": len(drift) == 0}


@router.get("/{part_id}/movements")
def part_movements(part_id: str, db: Session = Depends(get_db),
                   user: dict = Depends(get_current_user)):
    part = db.query(PartsInventory).filter(PartsInventory.id == part_id).first()
    if not part or part.organizationId != user.get("orgId"):
        raise HTTPException(status_code=404, detail="Part not found")

    rows = (
        db.query(StockMovement, User)
        .outerjoin(User, User.id == StockMovement.createdBy)
        .filter(StockMovement.partId == part_id)
        .order_by(StockMovement.createdAt.desc())
        .all()
    )
    return {
        "part": _serialise(part),
        "movements": [
            {
                "id": m.id,
                "delta": float(m.delta),
                "reason": m.reason,
                "refType": m.refType,
                "refId": m.refId,
                "by": u.name if u else None,
                "note": m.note,
                "createdAt": m.createdAt.isoformat() if m.createdAt else None,
            }
            for m, u in rows
        ],
    }


# ---------------------------------------------------------------------------
# Create and edit the catalogue
# ---------------------------------------------------------------------------

class PartCreate(BaseModel):
    name: str
    partNumber: Optional[str] = None
    unit: str = "pcs"
    category: Optional[str] = None
    reorderLevel: float = 0
    organizationId: str
    openingQuantity: float = Field(
        default=0,
        description="Stock counted on hand right now. Written as a ledger "
                    "receipt, never as a bare number, so the balance has "
                    "provenance from its first day.",
    )

    @field_validator("name")
    @classmethod
    def name_present(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("A part needs a name.")
        return v.strip()

    @field_validator("unit")
    @classmethod
    def unit_valid(cls, v: str) -> str:
        if v not in VALID_UNITS:
            raise ValueError(f"Unit must be one of: {', '.join(VALID_UNITS)}")
        return v


@router.post("/")
def create_part(
    body: PartCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(*MANAGER)),
):
    """Add a new part type to the catalogue.

    This is not the same act as receiving stock. Creating 'Copper pipe 1/2"'
    says you now stock that item; receiving 50m says 50m arrived. Conflating
    them is how inventory quietly stops matching the store.
    """
    if body.organizationId != user.get("orgId"):
        raise HTTPException(status_code=403, detail="Wrong organisation")

    if body.partNumber:
        clash = db.query(PartsInventory).filter(
            PartsInventory.organizationId == body.organizationId,
            PartsInventory.partNumber == body.partNumber.strip(),
        ).first()
        if clash:
            raise HTTPException(
                status_code=409,
                detail=f"Part number {body.partNumber} already exists ({clash.name}).",
            )

    part = PartsInventory(
        id=str(uuid.uuid4()),
        name=body.name,
        partNumber=(body.partNumber or "").strip() or None,
        quantity=0,
        reorderLevel=body.reorderLevel,
        unit=body.unit,
        category=(body.category or "").strip() or None,
        organizationId=body.organizationId,
        createdAt=_now(),
        updatedAt=_now(),
    )
    db.add(part)
    db.flush()

    if body.openingQuantity and body.openingQuantity > 0:
        record_movement(
            db,
            part_id=part.id,
            delta=body.openingQuantity,
            reason=StockReasonEnum.RECEIPT,
            created_by=user["sub"],
            ref_type="opening_balance",
            note="Opening stock at catalogue creation",
        )

    db.commit()
    db.refresh(part)
    return _serialise(part)


class PartUpdate(BaseModel):
    name: Optional[str] = None
    partNumber: Optional[str] = None
    unit: Optional[str] = None
    category: Optional[str] = None
    reorderLevel: Optional[float] = None

    @field_validator("unit")
    @classmethod
    def unit_valid(cls, v):
        if v is not None and v not in VALID_UNITS:
            raise ValueError(f"Unit must be one of: {', '.join(VALID_UNITS)}")
        return v


@router.patch("/{part_id}")
def update_part(
    part_id: str,
    body: PartUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(*MANAGER)),
):
    """Edit the catalogue entry. Quantity is deliberately not editable here —
    it moves only through the ledger."""
    part = db.query(PartsInventory).filter(PartsInventory.id == part_id).first()
    if not part or part.organizationId != user.get("orgId"):
        raise HTTPException(status_code=404, detail="Part not found")

    for key, value in body.model_dump(exclude_none=True).items():
        setattr(part, key, value)
    part.updatedAt = _now()

    db.commit()
    db.refresh(part)
    return _serialise(part)


# ---------------------------------------------------------------------------
# Stock movement
# ---------------------------------------------------------------------------

class AdjustRequest(BaseModel):
    delta: float = Field(description="Signed. Negative writes off, positive receives.")
    reason: StockReasonEnum
    note: Optional[str] = None


@router.post("/{part_id}/adjust")
def adjust_stock(
    part_id: str,
    body: AdjustRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(*MANAGER)),
):
    """Receipts, write-offs and corrections. Never an UPDATE on quantity."""
    part = db.query(PartsInventory).filter(PartsInventory.id == part_id).first()
    if not part or part.organizationId != user.get("orgId"):
        raise HTTPException(status_code=404, detail="Part not found")
    if body.reason == StockReasonEnum.JOB_CONSUMPTION:
        raise HTTPException(
            status_code=422,
            detail="Job consumption is written by report submission, not by hand.",
        )
    if body.delta == 0:
        raise HTTPException(status_code=422, detail="A zero adjustment records nothing.")

    record_movement(db, part_id=part_id, delta=body.delta, reason=body.reason,
                    created_by=user["sub"], ref_type="manual", note=body.note)
    db.commit()
    db.refresh(part)
    return {"part": _serialise(part), "delta": body.delta}


class ReceiveRequest(BaseModel):
    quantity: float
    note: Optional[str] = None

    @field_validator("quantity")
    @classmethod
    def positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Received quantity must be greater than zero.")
        return v


@router.post("/{part_id}/receive")
def receive_stock(
    part_id: str,
    body: ReceiveRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(*MANAGER)),
):
    """Stock arriving from a supplier. A plain-language wrapper over adjust,
    because 'receive 50' is what actually happens and 'delta +50' is not."""
    part = db.query(PartsInventory).filter(PartsInventory.id == part_id).first()
    if not part or part.organizationId != user.get("orgId"):
        raise HTTPException(status_code=404, detail="Part not found")

    record_movement(db, part_id=part_id, delta=body.quantity,
                    reason=StockReasonEnum.RECEIPT, created_by=user["sub"],
                    ref_type="manual", note=body.note)
    db.commit()
    db.refresh(part)
    return {"part": _serialise(part), "received": body.quantity}