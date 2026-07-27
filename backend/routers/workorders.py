from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import (
    AuditLog,
    MaintenanceLog,
    RoleEnum,
    User,
    WorkOrder,
    WorkOrderStatusEnum,
    PriorityEnum,
)
from routers.auth import get_current_user, get_current_user_optional, require_role
from routers.assignments import active_assignment
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid

router = APIRouter()

MANAGER_ROLES = (RoleEnum.MANAGER.value, RoleEnum.ADMIN.value)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


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
    overrideReason: Optional[str] = None


def _serialise(wo: WorkOrder, db: Session) -> dict:
    """Includes the assignee and the job age. The queue showed neither."""
    assignment = active_assignment(db, wo.id)
    technician = None
    if assignment:
        u = db.query(User).filter(User.id == assignment.userId).first()
        technician = {
            "id": assignment.userId,
            "name": u.name if u else None,
            "assignedAt": assignment.assignedAt.isoformat() if assignment.assignedAt else None,
            "acceptedAt": assignment.acceptedAt.isoformat() if assignment.acceptedAt else None,
            "accepted": assignment.acceptedAt is not None,
        }

    age_hours = None
    if wo.createdAt:
        age_hours = round((_now() - wo.createdAt).total_seconds() / 3600, 1)

    return {
        "id": wo.id,
        "title": wo.title,
        "description": wo.description,
        "priority": wo.priority.value if wo.priority else None,
        "status": wo.status.value if wo.status else None,
        "organizationId": wo.organizationId,
        "assetId": wo.assetId,
        "locationId": wo.locationId,
        "createdAt": wo.createdAt.isoformat() if wo.createdAt else None,
        "assignedAt": wo.assignedAt.isoformat() if wo.assignedAt else None,
        "acceptedAt": wo.acceptedAt.isoformat() if wo.acceptedAt else None,
        "reportedAt": wo.reportedAt.isoformat() if wo.reportedAt else None,
        "completedAt": wo.completedAt.isoformat() if wo.completedAt else None,
        "isLegacy": bool(wo.isLegacy),
        "technician": technician,
        "ageHours": age_hours,
        "ageDays": round(age_hours / 24, 1) if age_hours is not None else None,
    }


@router.get("/")
def get_workorders(organizationId: str, db: Session = Depends(get_db),
                   user: dict = Depends(get_current_user)):
    if organizationId != user.get("orgId"):
        raise HTTPException(status_code=403, detail="Wrong organisation")
    rows = db.query(WorkOrder).filter(
        WorkOrder.organizationId == organizationId
    ).order_by(WorkOrder.createdAt.desc()).all()
    return [_serialise(wo, db) for wo in rows]


@router.get("/{wo_id}")
def get_workorder(wo_id: str, db: Session = Depends(get_db),
                  user: dict = Depends(get_current_user)):
    wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
    if not wo or wo.organizationId != user.get("orgId"):
        raise HTTPException(status_code=404, detail="Work order not found")
    return _serialise(wo, db)


@router.post("/")
def create_workorder(
    wo: WorkOrderCreate,
    db: Session = Depends(get_db),
    user: dict | None = Depends(get_current_user_optional),
):
    """Public intake. The Client Portal has no login and must not acquire one.

    Raising a request is not a privileged act — a client reporting a broken
    chiller is the entry point of the whole system. Gating it would close the
    front door to protect the back office.

    What IS gated is everything downstream: who the job goes to, what state it
    reaches, and whether it can close without a report. A ticket created here
    starts OPEN and unassigned and cannot move until a manager touches it.
    """
    if user and wo.organizationId != user.get("orgId"):
        raise HTTPException(status_code=403, detail="Wrong organisation")
    now = _now()
    db_wo = WorkOrder(
        id=str(uuid.uuid4()),
        createdAt=now,
        updatedAt=now,
        isLegacy=False,
        **wo.model_dump(),
    )
    db.add(db_wo)
    db.commit()
    db.refresh(db_wo)
    return _serialise(db_wo, db)


@router.patch("/{wo_id}")
def update_workorder(
    wo_id: str,
    update: WorkOrderUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Status transitions are gated.

    Previously this accepted any status from an unauthenticated caller, so
    COMPLETED was one curl away. Two gates now apply to every work order created
    after cutover:

      Gate 1 — a job cannot leave OPEN without an assignee.
      Gate 2 — a job cannot reach COMPLETED without a filed report.

    Gate 2 has a manager override requiring a typed reason, written to the audit
    log. Jobs get closed by phone, technicians leave, records get backfilled.
    Blocking absolutely means people route around the system. Blocking with a
    logged reason shows you where the process actually breaks. Watch the override
    rate: if it climbs, the flow is wrong, not the people.
    """
    wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
    if not wo or wo.organizationId != user.get("orgId"):
        raise HTTPException(status_code=404, detail="Work order not found")

    is_manager = user.get("role") in MANAGER_ROLES
    new_status = update.status
    override_used = False
    reason = (update.overrideReason or "").strip() or None

    if new_status and new_status != wo.status and not wo.isLegacy:
        assignment = active_assignment(db, wo_id)

        # Gate 1
        if wo.status == WorkOrderStatusEnum.OPEN and not assignment:
            raise HTTPException(
                status_code=409,
                detail="Assign a technician before moving this job out of Open.",
            )

        # Gate 2
        if new_status == WorkOrderStatusEnum.COMPLETED:
            has_report = db.query(MaintenanceLog).filter(
                MaintenanceLog.workOrderId == wo_id
            ).first() is not None

            if not has_report:
                if not is_manager:
                    raise HTTPException(
                        status_code=409,
                        detail="File the field report to complete this job.",
                    )
                if not reason:
                    raise HTTPException(
                        status_code=422,
                        detail="Completing without a report requires a typed reason. "
                               "It is written to the audit log.",
                    )
                override_used = True
            if not assignment and not is_manager:
                raise HTTPException(
                    status_code=409,
                    detail="This job has no assigned technician.",
                )

    if not is_manager and (update.priority or update.description):
        raise HTTPException(
            status_code=403,
            detail="Only a manager can change priority or description.",
        )

    for key, value in update.model_dump(
        exclude_none=True, exclude={"overrideReason"}
    ).items():
        setattr(wo, key, value)

    if new_status == WorkOrderStatusEnum.COMPLETED and wo.completedAt is None:
        wo.completedAt = _now()

    if override_used:
        db.add(AuditLog(
            id=str(uuid.uuid4()),
            actorId=user["sub"],
            action="workorder.complete_override",
            entityType="WorkOrder",
            entityId=wo_id,
            reason=reason,
            metadata_json="no_report=true",
            createdAt=_now(),
        ))

    wo.updatedAt = _now()
    db.commit()
    db.refresh(wo)
    return _serialise(wo, db)


@router.delete("/{wo_id}")
def delete_workorder(
    wo_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(require_role(RoleEnum.ADMIN.value)),
):
    wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
    if not wo or wo.organizationId != user.get("orgId"):
        raise HTTPException(status_code=404, detail="Work order not found")
    db.delete(wo)
    db.commit()
    return {"message": "Work order deleted"}