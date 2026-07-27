"""Assignment, acceptance and reassignment.

WorkOrderAssignment already existed in the schema and was never written to by
anything. This is the code that writes it.

Assign and accept are different acts. Operations assigns — it knows who is where
and who is competent on which equipment. The technician acknowledges. Acceptance
stops meaning "claim" and starts meaning "seen it, going".

Reassignment closes the previous row and opens a new one. It never overwrites,
or the history credits the second technician for work the first started.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Asset,
    AuditLog,
    Location,
    User,
    WorkOrder,
    WorkOrderAssignment,
    WorkOrderStatusEnum,
    RoleEnum,
)
from routers.auth import get_current_user, require_role
from services.notifications import notify_assignment

router = APIRouter()

CLOSED_STATUSES = {WorkOrderStatusEnum.COMPLETED, WorkOrderStatusEnum.CANCELLED}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _audit(db: Session, actor_id: str, action: str, entity_id: str,
           reason: Optional[str] = None, metadata: Optional[str] = None) -> None:
    db.add(AuditLog(
        id=str(uuid.uuid4()),
        actorId=actor_id,
        action=action,
        entityType="WorkOrder",
        entityId=entity_id,
        reason=reason,
        metadata_json=metadata,
        createdAt=_now(),
    ))


def active_assignment(db: Session, wo_id: str) -> Optional[WorkOrderAssignment]:
    """The one row where unassignedAt IS NULL. Enforced by a partial unique index."""
    return (
        db.query(WorkOrderAssignment)
        .filter(
            WorkOrderAssignment.workOrderId == wo_id,
            WorkOrderAssignment.unassignedAt.is_(None),
        )
        .first()
    )


def _load_work_order(db: Session, wo_id: str, user: dict) -> WorkOrder:
    wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")
    if wo.organizationId != user.get("orgId"):
        # Do not leak existence across organisations.
        raise HTTPException(status_code=404, detail="Work order not found")
    return wo


# ---------------------------------------------------------------------------
# Assign / reassign
# ---------------------------------------------------------------------------

class AssignRequest(BaseModel):
    userId: str
    reason: Optional[str] = Field(
        default=None,
        description="Required when reassigning an already-assigned job.",
    )


@router.post("/{wo_id}/assign")
def assign_work_order(
    wo_id: str,
    body: AssignRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(RoleEnum.MANAGER.value, RoleEnum.ADMIN.value)),
):
    wo = _load_work_order(db, wo_id, user)

    if wo.status in CLOSED_STATUSES:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot assign a {wo.status.value.lower()} work order.",
        )

    technician = db.query(User).filter(User.id == body.userId).first()
    if not technician:
        raise HTTPException(status_code=404, detail="Technician not found")
    if technician.organizationId != user.get("orgId"):
        raise HTTPException(status_code=403, detail="Technician belongs to another organisation")
    if technician.isActive is False:
        raise HTTPException(status_code=409, detail=f"{technician.name} is not an active user")

    now = _now()
    current = active_assignment(db, wo_id)

    if current:
        if current.userId == body.userId:
            raise HTTPException(
                status_code=409,
                detail=f"Already assigned to {technician.name}.",
            )
        if not body.reason or not body.reason.strip():
            raise HTTPException(
                status_code=422,
                detail="Reassignment requires a reason. It is written to the audit log.",
            )
        # Close, do not overwrite.
        current.unassignedAt = now
        current.reason = body.reason.strip()
        _audit(db, user["sub"], "workorder.reassign", wo_id,
               reason=body.reason.strip(),
               metadata=f"from={current.userId} to={body.userId}")
        # A reassigned job has not been accepted by the new technician.
        wo.acceptedAt = None
    else:
        _audit(db, user["sub"], "workorder.assign", wo_id,
               metadata=f"to={body.userId}")

    db.add(WorkOrderAssignment(
        id=str(uuid.uuid4()),
        workOrderId=wo_id,
        userId=body.userId,
        assignedBy=user["sub"],
        assignedAt=now,
    ))

    wo.assignedAt = now
    wo.updatedAt = now
    db.commit()

    # Fire-and-forget. A notification failure must never fail an assignment.
    notify_assignment(work_order=wo, technician=technician, assigned_by=user.get("name"))

    return {
        "workOrderId": wo_id,
        "assignedTo": {"id": technician.id, "name": technician.name},
        "assignedAt": now.isoformat(),
        "reassigned": current is not None,
    }


# ---------------------------------------------------------------------------
# Accept
# ---------------------------------------------------------------------------

@router.post("/{wo_id}/accept")
def accept_work_order(
    wo_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    wo = _load_work_order(db, wo_id, user)
    current = active_assignment(db, wo_id)

    if not current:
        raise HTTPException(status_code=409, detail="This job has not been assigned to anyone.")
    if current.userId != user["sub"]:
        raise HTTPException(status_code=403, detail="This job is assigned to another technician.")
    if current.acceptedAt is not None:
        return {"workOrderId": wo_id, "acceptedAt": current.acceptedAt.isoformat(),
                "alreadyAccepted": True}

    now = _now()
    current.acceptedAt = now
    wo.acceptedAt = now
    if wo.status == WorkOrderStatusEnum.OPEN:
        wo.status = WorkOrderStatusEnum.IN_PROGRESS
    wo.updatedAt = now

    _audit(db, user["sub"], "workorder.accept", wo_id)
    db.commit()

    delay = (now - current.assignedAt).total_seconds() / 3600 if current.assignedAt else None
    return {
        "workOrderId": wo_id,
        "acceptedAt": now.isoformat(),
        "status": wo.status.value,
        "hoursToAccept": round(delay, 2) if delay is not None else None,
    }


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

@router.get("/mine")
def my_work_orders(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """A technician sees only his own jobs. Unaccepted first — that is the in-app badge."""
    rows = (
        db.query(WorkOrder, WorkOrderAssignment, Asset, Location)
        .join(WorkOrderAssignment, WorkOrderAssignment.workOrderId == WorkOrder.id)
        .outerjoin(Asset, Asset.id == WorkOrder.assetId)
        .outerjoin(Location, Location.id == WorkOrder.locationId)
        .filter(
            WorkOrderAssignment.userId == user["sub"],
            WorkOrderAssignment.unassignedAt.is_(None),
            WorkOrder.status.notin_(list(CLOSED_STATUSES)),
        )
        .all()
    )

    now = _now()
    jobs = []
    for wo, asn, asset, location in rows:
        assigned_at = asn.assignedAt or wo.createdAt
        jobs.append({
            "id": wo.id,
            "title": wo.title,
            "description": wo.description,
            "priority": wo.priority.value if wo.priority else None,
            "status": wo.status.value if wo.status else None,
            "assetId": wo.assetId,
            "assetName": asset.name if asset else None,
            "locationId": wo.locationId,
            "locationName": location.name if location else None,
            # The technician needs to know where to drive, not a uuid.
            "address": location.address if location else None,
            "createdAt": wo.createdAt.isoformat() if wo.createdAt else None,
            "assignedAt": asn.assignedAt.isoformat() if asn.assignedAt else None,
            "acceptedAt": asn.acceptedAt.isoformat() if asn.acceptedAt else None,
            "accepted": asn.acceptedAt is not None,
            "ageHours": round((now - assigned_at).total_seconds() / 3600, 1) if assigned_at else None,
        })

    jobs.sort(key=lambda j: (j["accepted"], -(j["ageHours"] or 0)))
    return jobs


@router.get("/{wo_id}/assignments")
def assignment_history(
    wo_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    _load_work_order(db, wo_id, user)
    rows = (
        db.query(WorkOrderAssignment, User)
        .outerjoin(User, User.id == WorkOrderAssignment.userId)
        .filter(WorkOrderAssignment.workOrderId == wo_id)
        .order_by(WorkOrderAssignment.assignedAt.asc())
        .all()
    )
    return [
        {
            "id": a.id,
            "technician": {"id": a.userId, "name": u.name if u else None},
            "assignedBy": a.assignedBy,
            "assignedAt": a.assignedAt.isoformat() if a.assignedAt else None,
            "acceptedAt": a.acceptedAt.isoformat() if a.acceptedAt else None,
            "unassignedAt": a.unassignedAt.isoformat() if a.unassignedAt else None,
            "reason": a.reason,
            "active": a.unassignedAt is None,
        }
        for a, u in rows
    ]