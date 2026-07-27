"""Parts catalogue and stock ledger.

The technician app read its parts list from lib/data.ts, a static mock. These are
the endpoints that replace it with the PartsInventory table that already existed
and was never exposed.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
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


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.get("/")
def list_parts(organizationId: str, db: Session = Depends(get_db),
               user: dict = Depends(get_current_user)):
    if organizationId != user.get("orgId"):
        raise HTTPException(status_code=403, detail="Wrong organisation")
    parts = (
        db.query(PartsInventory)
        .filter(PartsInventory.organizationId == organizationId)
        .order_by(PartsInventory.name.asc())
        .all()
    )
    return [
        {
            "id": p.id,
            "name": p.name,
            "partNumber": p.partNumber,
            "quantity": p.quantity,
            "reorderLevel": p.reorderLevel,
            "lowStock": (p.quantity or 0) <= (p.reorderLevel or 0),
        }
        for p in parts
    ]


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
    return {"count": len(parts),
            "parts": [{"id": p.id, "name": p.name, "quantity": p.quantity,
                       "reorderLevel": p.reorderLevel} for p in parts]}


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
        "part": {"id": part.id, "name": part.name, "quantity": part.quantity},
        "movements": [
            {
                "id": m.id,
                "delta": m.delta,
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


class AdjustRequest(BaseModel):
    delta: int = Field(description="Signed. Negative writes off, positive receives.")
    reason: StockReasonEnum
    note: Optional[str] = None


@router.post("/{part_id}/adjust")
def adjust_stock(
    part_id: str,
    body: AdjustRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(RoleEnum.MANAGER.value, RoleEnum.ADMIN.value)),
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
    return {"partId": part_id, "quantity": part.quantity, "delta": body.delta}


@router.get("/reconcile")
def run_reconcile(db: Session = Depends(get_db),
                  user: dict = Depends(require_role(RoleEnum.ADMIN.value))):
    """Cached balance vs ledger. A non-empty result is a bug, not a report."""
    drift = reconcile(db)
    return {"drift": drift, "clean": len(drift) == 0}