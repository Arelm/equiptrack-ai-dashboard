"""
EquipTrack AI — Asset Transfer models & schemas (v2).

Matched to the live Aurora schema: PascalCase tables, camelCase columns,
TEXT ids. Uses its own declarative Base on purpose — the table already
exists from migration 002, so nothing here runs create_all, and there is
no dependency on your existing model classes.

Integration: nothing to change in this file.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.orm import declarative_base

TransferBase = declarative_base()

VALID_REASONS = {"PROJECT_NEED", "SITE_DEMOB", "REPAIR", "STORAGE", "OTHER"}


# ---------------------------------------------------------------- SQLAlchemy

class AssetTransfer(TransferBase):
    __tablename__ = "AssetTransfer"

    id = Column(String, primary_key=True)
    assetId = Column("assetId", String, nullable=False, index=True)

    fromLocationId = Column("fromLocationId", String, nullable=False)
    toLocationId = Column("toLocationId", String, nullable=False)

    reason = Column(String, nullable=False, default="PROJECT_NEED")
    notes = Column(Text, nullable=True)

    status = Column(String, nullable=False, default="IN_TRANSIT", index=True)

    initiatedById = Column("initiatedById", String, nullable=True)
    receivedById = Column("receivedById", String, nullable=True)

    conditionOnDispatch = Column("conditionOnDispatch", String, nullable=True)
    conditionOnArrival = Column("conditionOnArrival", String, nullable=True)

    initiatedAt = Column("initiatedAt", DateTime, nullable=False,
                         default=datetime.utcnow)
    resolvedAt = Column("resolvedAt", DateTime, nullable=True)


# ---------------------------------------------------------------- Pydantic

class TransferCreate(BaseModel):
    assetId: str
    toLocationId: str
    reason: str = Field(default="PROJECT_NEED")
    notes: Optional[str] = None
    conditionOnDispatch: Optional[str] = Field(default=None, max_length=255)
    initiatedById: Optional[str] = None  # -> current_user.id once auth lands


class TransferReceive(BaseModel):
    conditionOnArrival: Optional[str] = Field(default=None, max_length=255)
    receivedById: Optional[str] = None   # -> current_user.id once auth lands


class TransferDispute(BaseModel):
    notes: str = Field(..., min_length=3)
    receivedById: Optional[str] = None


class TransferOut(BaseModel):
    id: str
    assetId: str
    fromLocationId: str
    toLocationId: str
    fromLocationName: Optional[str] = None   # joined in for display
    toLocationName: Optional[str] = None
    reason: str
    notes: Optional[str]
    status: str
    initiatedById: Optional[str]
    receivedById: Optional[str]
    conditionOnDispatch: Optional[str]
    conditionOnArrival: Optional[str]
    initiatedAt: datetime
    resolvedAt: Optional[datetime]

    class Config:
        from_attributes = True


class LocationOut(BaseModel):
    id: str
    name: str
    address: Optional[str] = None
