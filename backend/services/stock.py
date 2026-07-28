"""Stock as an append-only ledger.

PartsInventory.quantity is a cached read. StockMovement is the truth.

A wrong quantity, an edited report, or a returned part is handled by writing a
compensating movement — never by editing or deleting an existing one. The ledger
only grows. This is the same rule the codebase already applies to assignment
history, for the same reason: a mutated number destroys the audit trail that
makes the number worth having.
"""

import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import PartsInventory, StockMovement, StockReasonEnum


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def record_movement(
    db: Session,
    part_id: str,
    delta: int | float | Decimal,
    reason: StockReasonEnum,
    created_by: Optional[str] = None,
    ref_type: Optional[str] = None,
    ref_id: Optional[str] = None,
    note: Optional[str] = None,
) -> StockMovement:
    """Write one ledger row and update the cached balance in the same transaction.

    Does not commit. The caller owns the transaction boundary so a report and all
    of its stock movements succeed or fail together.
    """
    # quantity is numeric in Postgres, so SQLAlchemy hands back a Decimal
    # while the API sends a float. Mixing them raises TypeError, so the
    # delta becomes Decimal at the door. str() first: Decimal(0.1) is not
    # 0.1, but Decimal("0.1") is.
    delta = Decimal(str(delta))

    if delta == 0:
        raise ValueError("A zero-delta movement records nothing.")

    movement = StockMovement(
        id=str(uuid.uuid4()),
        partId=part_id,
        delta=delta,
        reason=reason.value,
        refType=ref_type,
        refId=ref_id,
        createdBy=created_by,
        note=note,
        createdAt=_now(),
    )
    db.add(movement)

    part = db.query(PartsInventory).filter(PartsInventory.id == part_id).first()
    if part is not None:
        part.quantity = (part.quantity or 0) + delta
        part.updatedAt = _now()

    return movement


def consume_for_report(
    db: Session,
    part_id: str,
    quantity: int,
    report_id: str,
    created_by: Optional[str],
) -> StockMovement:
    return record_movement(
        db,
        part_id=part_id,
        delta=-abs(quantity),
        reason=StockReasonEnum.JOB_CONSUMPTION,
        created_by=created_by,
        ref_type="MaintenanceLog",
        ref_id=report_id,
    )


def reconcile(db: Session) -> list[dict]:
    """Compare the cached balance against the ledger.

    A mismatch is a bug. You want to be told, not to discover it in six months.
    Run nightly. Opening balances predate the ledger, so a part with no movements
    is skipped rather than reported.
    """
    ledger = dict(
        db.query(StockMovement.partId, func.sum(StockMovement.delta))
        .group_by(StockMovement.partId)
        .all()
    )

    drift = []
    for part in db.query(PartsInventory).all():
        if part.id not in ledger:
            continue
        movements = db.query(StockMovement).filter(
            StockMovement.partId == part.id
        ).order_by(StockMovement.createdAt.asc()).all()
        opening = (part.quantity or 0) - sum(m.delta for m in movements)
        expected = opening + ledger[part.id]
        if expected != (part.quantity or 0):
            drift.append({
                "partId": part.id,
                "partName": part.name,
                "cached": part.quantity,
                "expected": expected,
                "difference": (part.quantity or 0) - expected,
            })
    return drift