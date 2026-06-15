from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Asset, AssetStatusEnum
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

router = APIRouter()

class AssetCreate(BaseModel):
    name: str
    serialNumber: Optional[str] = None
    category: str
    organizationId: str
    locationId: Optional[str] = None
    purchaseDate: Optional[datetime] = None
    warrantyExpiry: Optional[datetime] = None

class AssetUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[AssetStatusEnum] = None
    locationId: Optional[str] = None
    warrantyExpiry: Optional[datetime] = None

@router.get("/")
def get_assets(organizationId: str, db: Session = Depends(get_db)):
    return db.query(Asset).filter(Asset.organizationId == organizationId).all()

@router.get("/{asset_id}")
def get_asset(asset_id: str, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset

@router.post("/")
def create_asset(asset: AssetCreate, db: Session = Depends(get_db)):
    db_asset = Asset(id=str(uuid.uuid4()), **asset.model_dump())
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    return db_asset

@router.patch("/{asset_id}")
def update_asset(asset_id: str, update: AssetUpdate, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    for key, value in update.model_dump(exclude_none=True).items():
        setattr(asset, key, value)
    db.commit()
    db.refresh(asset)
    return asset

@router.delete("/{asset_id}")
def delete_asset(asset_id: str, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    db.delete(asset)
    db.commit()
    return {"message": "Asset deleted"}