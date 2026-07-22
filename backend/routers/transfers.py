"""
EquipTrack AI — Asset Transfer router (v2, matched to live schema).

File placement (matches the equiptrack repo layout):
    models_transfers.py -> repo root, next to models.py
    transfers.py        -> routers/

Wire-up in main.py (two edits):
    line 3:  from routers import assets, workorders, ..., transfers
    add:     app.include_router(transfers.router, prefix="/api/transfers", tags=["Transfers"])

No other changes needed — get_db comes from database.py as in your other routers.

When auth (hardening item 2) ships: replace initiatedById/receivedById body
fields with the authenticated user's id and remove them from the schemas.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db  # <-- adjust to your project's session dependency

from routers.auth import get_current_user_optional

from models_transfers import (
    VALID_REASONS,
    AssetTransfer,
    LocationOut,
    TransferCreate,
    TransferDispute,
    TransferOut,
    TransferReceive,
)

router = APIRouter()  # prefix="/api/transfers" is applied in main.py, per project convention


# ------------------------------------------------------------ helpers

def _asset(db: Session, asset_id: str):
    row = db.execute(
        text('SELECT id, name, "locationId", "custodyStatus" FROM "Asset" WHERE id = :id'),
        {"id": asset_id},
    ).first()
    if not row:
        raise HTTPException(404, "Asset not found")
    return row


def _location_exists(db: Session, location_id: str) -> bool:
    return db.execute(
        text('SELECT 1 FROM "Location" WHERE id = :id'), {"id": location_id}
    ).first() is not None


def _set_asset(db: Session, asset_id: str, *, custody: str, location_id: str | None = None):
    if location_id:
        db.execute(
            text('UPDATE "Asset" SET "custodyStatus" = :c, "locationId" = :l, '
                 '"updatedAt" = NOW() WHERE id = :id'),
            {"c": custody, "l": location_id, "id": asset_id},
        )
    else:
        db.execute(
            text('UPDATE "Asset" SET "custodyStatus" = :c, "updatedAt" = NOW() '
                 'WHERE id = :id'),
            {"c": custody, "id": asset_id},
        )


def _get_transfer(db: Session, transfer_id: str) -> AssetTransfer:
    t = db.query(AssetTransfer).filter(AssetTransfer.id == transfer_id).first()
    if not t:
        raise HTTPException(404, "Transfer not found")
    return t


_LOCATION_NAMES = text('SELECT id, name FROM "Location"')


def _with_names(db: Session, transfers: list[AssetTransfer]) -> list[TransferOut]:
    names = {r[0]: r[1] for r in db.execute(_LOCATION_NAMES).fetchall()}
    out = []
    for t in transfers:
        o = TransferOut.model_validate(t)
        o.fromLocationName = names.get(t.fromLocationId)
        o.toLocationName = names.get(t.toLocationId)
        out.append(o)
    return out


# ------------------------------------------------------------ initiate

@router.post("", response_model=TransferOut, status_code=201)
def initiate_transfer(payload: TransferCreate, db: Session = Depends(get_db),
                      user: dict | None = Depends(get_current_user_optional)):
    asset = _asset(db, payload.assetId)

    if payload.reason not in VALID_REASONS:
        raise HTTPException(422, f"reason must be one of {sorted(VALID_REASONS)}")
    if not _location_exists(db, payload.toLocationId):
        raise HTTPException(404, "Destination location not found")
    if payload.toLocationId == asset.locationId:
        raise HTTPException(422, "Asset is already at that location")

    open_transfer = (
        db.query(AssetTransfer)
        .filter(AssetTransfer.assetId == asset.id,
                AssetTransfer.status == "IN_TRANSIT")
        .first()
    )
    if open_transfer:
        raise HTTPException(
            409, "Asset already has an open transfer. Receive, dispute, or "
                 "cancel it before initiating another."
        )

    transfer = AssetTransfer(
        id=str(uuid.uuid4()),
        assetId=asset.id,
        fromLocationId=asset.locationId,   # snapshot the origin
        toLocationId=payload.toLocationId,
        reason=payload.reason,
        notes=payload.notes,
        conditionOnDispatch=payload.conditionOnDispatch,
        initiatedById=user["sub"] if user else payload.initiatedById,
        status="IN_TRANSIT",
        initiatedAt=datetime.utcnow(),
    )
    db.add(transfer)
    _set_asset(db, asset.id, custody="IN_TRANSIT")   # location stays = origin

    db.commit()
    db.refresh(transfer)
    return _with_names(db, [transfer])[0]


# ------------------------------------------------------------ receive

@router.post("/{transfer_id}/receive", response_model=TransferOut)
def receive_transfer(transfer_id: str, payload: TransferReceive,
                     db: Session = Depends(get_db),
                     user: dict | None = Depends(get_current_user_optional)):
    t = _get_transfer(db, transfer_id)
    if t.status != "IN_TRANSIT":
        raise HTTPException(409, f"Transfer is {t.status}, not IN_TRANSIT")

    t.status = "RECEIVED"
    t.receivedById = user["sub"] if user else payload.receivedById
    t.conditionOnArrival = payload.conditionOnArrival
    t.resolvedAt = datetime.utcnow()

    # location updates ONLY here — this is what makes the trail auditable
    _set_asset(db, t.assetId, custody="ON_SITE", location_id=t.toLocationId)

    db.commit()
    db.refresh(t)
    return _with_names(db, [t])[0]


# ------------------------------------------------------------ dispute

@router.post("/{transfer_id}/dispute", response_model=TransferOut)
def dispute_transfer(transfer_id: str, payload: TransferDispute,
                     db: Session = Depends(get_db),
                    user: dict | None = Depends(get_current_user_optional)):
    t = _get_transfer(db, transfer_id)
    if t.status != "IN_TRANSIT":
        raise HTTPException(409, f"Transfer is {t.status}, not IN_TRANSIT")

    t.status = "DISPUTED"
    t.receivedById = user["sub"] if user else payload.receivedById
    t.notes = (t.notes + "\n--- DISPUTE ---\n" if t.notes else "") + payload.notes
    t.resolvedAt = datetime.utcnow()

    _set_asset(db, t.assetId, custody="DISPUTED")

    db.commit()
    db.refresh(t)
    return _with_names(db, [t])[0]


# ------------------------------------------------------------ cancel

@router.post("/{transfer_id}/cancel", response_model=TransferOut)
def cancel_transfer(transfer_id: str, db: Session = Depends(get_db)):
    t = _get_transfer(db, transfer_id)
    if t.status != "IN_TRANSIT":
        raise HTTPException(409, f"Transfer is {t.status}, not IN_TRANSIT")

    t.status = "CANCELLED"
    t.resolvedAt = datetime.utcnow()

    _set_asset(db, t.assetId, custody="ON_SITE")

    db.commit()
    db.refresh(t)
    return _with_names(db, [t])[0]


# ------------------------------------------------------------ queries

@router.get("", response_model=list[TransferOut])
def list_transfers(
    status: str | None = Query(default=None),
    assetId: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    q = db.query(AssetTransfer)
    if status:
        q = q.filter(AssetTransfer.status == status.upper())
    if assetId:
        q = q.filter(AssetTransfer.assetId == assetId)
    rows = q.order_by(AssetTransfer.initiatedAt.desc()).limit(200).all()
    return _with_names(db, rows)


@router.get("/locations", response_model=list[LocationOut])
def list_locations(db: Session = Depends(get_db)):
    """Feeds the destination dropdown in the frontend."""
    rows = db.execute(
        text('SELECT id, name, address FROM "Location" ORDER BY name')
    ).fetchall()
    return [LocationOut(id=r[0], name=r[1], address=r[2]) for r in rows]


@router.get("/asset/{asset_id}", response_model=list[TransferOut])
def asset_movement_history(asset_id: str, db: Session = Depends(get_db)):
    """Full custody trail for one asset, newest first."""
    rows = (
        db.query(AssetTransfer)
        .filter(AssetTransfer.assetId == asset_id)
        .order_by(AssetTransfer.initiatedAt.desc())
        .all()
    )
    return _with_names(db, rows)
