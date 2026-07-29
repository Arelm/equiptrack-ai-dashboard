"""Field report submission.

The form previously called preventDefault() and showed a success message. Nothing
was written. This is the endpoint it should have been posting to.

One report per job. The job is taken from the URL, never from a dropdown — the
Daikin/Gree mis-attribution on ticket a4c11f69 was a dropdown selection error and
this removes the dropdown from existence.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.orm import Session

from database import get_db
from models import (
    AuditLog,
    MaintenanceLog,
    PartsInventory,
    PartsUsed,
    PartSourceEnum,
    RoleEnum,
    STOCK_BEARING_SOURCES,
    User,
    WorkOrder,
    WorkOrderStatusEnum,
)
from routers.assignments import active_assignment
from routers.auth import get_current_user
from services.stock import consume_for_report

router = APIRouter()

MANAGER_ROLES = {RoleEnum.MANAGER.value, RoleEnum.ADMIN.value}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class PartLine(BaseModel):
    partId: Optional[str] = None
    partNameRaw: Optional[str] = Field(
        default=None,
        description='Free text from "Part not listed". A technician who cannot '
                    'find his part will otherwise log nothing at all.',
    )
    quantity: Decimal = Decimal("1")
    source: PartSourceEnum

    @field_validator("quantity")
    @classmethod
    def positive(cls, v: Decimal) -> Decimal:
        # Not "at least 1" - half a metre of insulation is a real quantity.
        # Zero is not: a line with no quantity is a line that should not exist.
        if v <= 0:
            raise ValueError("Quantity must be greater than zero.")
        return v

    @model_validator(mode="after")
    def identified(self):
        if not self.partId and not (self.partNameRaw or "").strip():
            raise ValueError("Each parts line needs either a catalogue part or a typed name.")
        return self


class ReportCreate(BaseModel):
    notes: str
    hoursSpent: Optional[float] = None
    partsUsed: bool = Field(
        description="Explicit declaration. False means the technician stated no "
                    "parts were needed — a real and useful data point, not a blank."
    )
    parts: List[PartLine] = []
    overrideReason: Optional[str] = None

    @field_validator("notes")
    @classmethod
    def notes_present(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Work notes are required.")
        return v.strip()

    @model_validator(mode="after")
    def declaration_matches(self):
        if self.partsUsed and not self.parts:
            raise ValueError('Parts declared as used but no lines supplied. '
                             'Either add a line or declare "no parts needed".')
        if not self.partsUsed and self.parts:
            raise ValueError('Parts supplied but declared as unused. Set partsUsed to true.')
        return self


@router.post("/workorders/{wo_id}/report")
def submit_report(
    wo_id: str,
    body: ReportCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
    if not wo or wo.organizationId != user.get("orgId"):
        raise HTTPException(status_code=404, detail="Work order not found")

    is_manager = user.get("role") in MANAGER_ROLES

    # --- Gate: one report per job -------------------------------------------
    existing = db.query(MaintenanceLog).filter(MaintenanceLog.workOrderId == wo_id).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="A report has already been filed for this job. "
                   "Corrections are filed as amendments, not overwrites.",
        )

    # --- Gate: the assigned technician files the report ----------------------
    assignment = active_assignment(db, wo_id)
    if not wo.isLegacy:
        if not assignment:
            raise HTTPException(
                status_code=409,
                detail="This job has no assigned technician. Assign it first.",
            )
        if assignment.userId != user["sub"] and not is_manager:
            raise HTTPException(
                status_code=403,
                detail="This job is assigned to another technician.",
            )
        if assignment.acceptedAt is None and not is_manager:
            raise HTTPException(
                status_code=409,
                detail="Accept the job before filing a report.",
            )
        if wo.status in (WorkOrderStatusEnum.COMPLETED, WorkOrderStatusEnum.CANCELLED):
            raise HTTPException(
                status_code=409,
                detail=f"This job is already {wo.status.value.lower()}.",
            )

    # A manager filing on someone else's behalf is legitimate and logged.
    manager_override = bool(
        is_manager and assignment and assignment.userId != user["sub"]
    )
    if manager_override and not (body.overrideReason or "").strip():
        raise HTTPException(
            status_code=422,
            detail="Filing on behalf of another technician requires a reason.",
        )

    now = _now()
    report_id = str(uuid.uuid4())

    # --- Validate every part line before writing anything --------------------
    resolved: list[tuple[PartLine, Optional[PartsInventory]]] = []
    for line in body.parts:
        part = None
        if line.partId:
            part = db.query(PartsInventory).filter(PartsInventory.id == line.partId).first()
            if not part:
                raise HTTPException(status_code=404, detail=f"Unknown part: {line.partId}")
            if part.organizationId != user.get("orgId"):
                raise HTTPException(status_code=403, detail="Part belongs to another organisation")
        resolved.append((line, part))

    # --- Write ---------------------------------------------------------------
    db.add(MaintenanceLog(
        id=report_id,
        workOrderId=wo_id,
        assetId=wo.assetId,          # denormalised so history survives ticket edits
        userId=assignment.userId if assignment else user["sub"],
        notes=body.notes,
        hoursSpent=body.hoursSpent,
        partsUsedDeclared=body.partsUsed,
        createdAt=now,
    ))

    stock_moved = []
    for line, part in resolved:
        db.add(PartsUsed(
            id=str(uuid.uuid4()),
            maintenanceLogId=report_id,
            partId=line.partId,
            partNameRaw=(line.partNameRaw or "").strip() or None,
            quantityUsed=line.quantity,
            source=line.source.value,
            createdAt=now,
        ))

        # Only sources that came out of inventory you own draw it down.
        # purchased_on_site and client_supplied never entered it.
        if part is not None and line.source in STOCK_BEARING_SOURCES:
            consume_for_report(
                db,
                part_id=part.id,
                quantity=line.quantity,
                report_id=report_id,
                created_by=user["sub"],
            )
            stock_moved.append({"part": part.name, "delta": -line.quantity})

    # Filing the report is the completion. Reported and Resolved do not need
    # to be separate states for a five-technician shop.
    wo.reportedAt = now
    wo.completedAt = now
    wo.status = WorkOrderStatusEnum.COMPLETED
    wo.updatedAt = now

    db.add(AuditLog(
        id=str(uuid.uuid4()),
        actorId=user["sub"],
        action="workorder.report_filed",
        entityType="WorkOrder",
        entityId=wo_id,
        reason=(body.overrideReason or "").strip() or None,
        metadata_json=f"reportId={report_id} parts={len(body.parts)} override={manager_override}",
        createdAt=now,
    ))

    db.commit()

    return {
        "reportId": report_id,
        "workOrderId": wo_id,
        "status": wo.status.value,
        "partsLogged": len(body.parts),
        "partsDeclared": body.partsUsed,
        "stockMovements": stock_moved,
    }


@router.get("/workorders/{wo_id}/report")
def get_report(wo_id: str, db: Session = Depends(get_db),
               user: dict = Depends(get_current_user)):
    wo = db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()
    if not wo or wo.organizationId != user.get("orgId"):
        raise HTTPException(status_code=404, detail="Work order not found")

    log = db.query(MaintenanceLog).filter(MaintenanceLog.workOrderId == wo_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="No report filed for this job")

    return _serialise(db, log)


@router.get("/assets/{asset_id}/history")
def asset_history(asset_id: str, db: Session = Depends(get_db),
                  user: dict = Depends(get_current_user)):
    """Every report and every part ever fitted to this asset.

    This is what compounds. It is also what the AI analysis prompt should read
    instead of a single ticket's fault description.
    """
    logs = (
        db.query(MaintenanceLog)
        .filter(MaintenanceLog.assetId == asset_id)
        .order_by(MaintenanceLog.createdAt.desc())
        .all()
    )
    return [_serialise(db, log) for log in logs]


def _serialise(db: Session, log: MaintenanceLog) -> dict:
    lines = db.query(PartsUsed).filter(PartsUsed.maintenanceLogId == log.id).all()
    catalogue = {
        p.id: p.name for p in db.query(PartsInventory).filter(
            PartsInventory.id.in_([l.partId for l in lines if l.partId] or [""])
        ).all()
    }
    technician = db.query(User).filter(User.id == log.userId).first()

    return {
        "id": log.id,
        "workOrderId": log.workOrderId,
        "assetId": log.assetId,
        "technician": {"id": log.userId, "name": technician.name if technician else None},
        "notes": log.notes,
        "hoursSpent": log.hoursSpent,
        "partsUsedDeclared": log.partsUsedDeclared,
        "createdAt": log.createdAt.isoformat() if log.createdAt else None,
        "parts": [
            {
                "id": l.id,
                "partId": l.partId,
                "name": catalogue.get(l.partId) or l.partNameRaw,
                "fromCatalogue": l.partId is not None,
                "quantity": l.quantityUsed,
                "source": l.source,
            }
            for l in lines
        ],
    }