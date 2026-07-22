"""
EquipTrack AI — Asset Disposal router.

File placement:  routers/disposals.py
Wire-up in main.py:
    line 3:  add `disposals` to the `from routers import ...` line
    add:     app.include_router(disposals.router, prefix="/api/disposals", tags=["Disposals"])

Design:
  - Disposing an asset sets Asset.status = 'DECOMMISSIONED' (existing enum value)
    and writes one AssetDisposal record (method, reason, confirmedBy, timestamp).
  - One disposal per asset (UNIQUE assetId). Restore deletes the record and
    returns the asset to OPERATIONAL — the escape hatch for mis-clicks.
  - An asset with an open IN_TRANSIT transfer cannot be disposed.
"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db

router = APIRouter()

VALID_METHODS = {"SCRAPPED", "SOLD", "DONATED", "RETURNED", "LOST_STOLEN"}


# ---------------------------------------------------------------- schemas

class DisposalCreate(BaseModel):
    assetId: str
    method: str = Field(default="SCRAPPED")
    reason: Optional[str] = None
    confirmedById: Optional[str] = None  # -> current_user.id once auth lands


class DisposalOut(BaseModel):
    id: str
    assetId: str
    assetName: Optional[str] = None
    assetCategory: Optional[str] = None
    lastLocationName: Optional[str] = None
    method: str
    reason: Optional[str]
    confirmedById: Optional[str]
    disposedAt: datetime


# ---------------------------------------------------------------- helpers

_SELECT_DISPOSALS = text('''
    SELECT d.id, d."assetId", d.method, d.reason, d."confirmedById", d."disposedAt",
           a.name, a.category, l.name AS location_name
    FROM "AssetDisposal" d
    JOIN "Asset" a ON a.id = d."assetId"
    LEFT JOIN "Location" l ON l.id = a."locationId"
''')


def _row_to_out(r) -> DisposalOut:
    return DisposalOut(
        id=r.id, assetId=r.assetId, method=r.method, reason=r.reason,
        confirmedById=r.confirmedById, disposedAt=r.disposedAt,
        assetName=r.name, assetCategory=r.category, lastLocationName=r.location_name,
    )


# ---------------------------------------------------------------- dispose

@router.post("", response_model=DisposalOut, status_code=201)
def dispose_asset(payload: DisposalCreate, db: Session = Depends(get_db)):
    if payload.method not in VALID_METHODS:
        raise HTTPException(422, f"method must be one of {sorted(VALID_METHODS)}")

    asset = db.execute(
        text('SELECT id, status FROM "Asset" WHERE id = :id'),
        {"id": payload.assetId},
    ).first()
    if not asset:
        raise HTTPException(404, "Asset not found")
    if asset.status == "DECOMMISSIONED":
        raise HTTPException(409, "Asset is already decommissioned")

    open_transfer = db.execute(
        text('SELECT 1 FROM "AssetTransfer" WHERE "assetId" = :id '
             "AND status = 'IN_TRANSIT'"),
        {"id": payload.assetId},
    ).first()
    if open_transfer:
        raise HTTPException(
            409, "Asset has an open transfer. Receive, dispute, or cancel it "
                 "before disposal."
        )

    disposal_id = str(uuid.uuid4())
    db.execute(
        text('INSERT INTO "AssetDisposal" '
             '(id, "assetId", method, reason, "confirmedById", "disposedAt") '
             'VALUES (:id, :aid, :m, :r, :cb, NOW())'),
        {"id": disposal_id, "aid": payload.assetId, "m": payload.method,
         "r": payload.reason, "cb": payload.confirmedById},
    )
    db.execute(
        text('UPDATE "Asset" SET status = \'DECOMMISSIONED\', "updatedAt" = NOW() '
             'WHERE id = :id'),
        {"id": payload.assetId},
    )
    db.commit()

    row = db.execute(
        text(str(_SELECT_DISPOSALS.text) + ' WHERE d.id = :id'), {"id": disposal_id}
    ).first()
    return _row_to_out(row)


# ---------------------------------------------------------------- restore

@router.post("/{disposal_id}/restore", response_model=dict)
def restore_asset(disposal_id: str, db: Session = Depends(get_db)):
    d = db.execute(
        text('SELECT id, "assetId" FROM "AssetDisposal" WHERE id = :id'),
        {"id": disposal_id},
    ).first()
    if not d:
        raise HTTPException(404, "Disposal record not found")

    db.execute(text('DELETE FROM "AssetDisposal" WHERE id = :id'), {"id": d.id})
    db.execute(
        text('UPDATE "Asset" SET status = \'OPERATIONAL\', "updatedAt" = NOW() '
             'WHERE id = :id'),
        {"id": d.assetId},
    )
    db.commit()
    return {"restored": True, "assetId": d.assetId}


# ---------------------------------------------------------------- queries

@router.get("", response_model=list[DisposalOut])
def list_disposals(
    method: str | None = Query(default=None),
    organizationId: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    sql = str(_SELECT_DISPOSALS.text)
    clauses, params = [], {}
    if method:
        clauses.append("d.method = :m")
        params["m"] = method.upper()
    if organizationId:
        clauses.append('a."organizationId" = :org')
        params["org"] = organizationId
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += ' ORDER BY d."disposedAt" DESC LIMIT 200'
    rows = db.execute(text(sql), params).fetchall()
    return [_row_to_out(r) for r in rows]


@router.get("/asset/{asset_id}", response_model=DisposalOut)
def asset_disposal(asset_id: str, db: Session = Depends(get_db)):
    row = db.execute(
        text(str(_SELECT_DISPOSALS.text) + ' WHERE d."assetId" = :id'),
        {"id": asset_id},
    ).first()
    if not row:
        raise HTTPException(404, "No disposal record for this asset")
    return _row_to_out(row)
