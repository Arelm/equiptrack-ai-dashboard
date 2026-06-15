from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import Alert

router = APIRouter()

@router.get("/")
def get_alerts(organizationId: str, db: Session = Depends(get_db)):
    return db.query(Alert).filter(
        Alert.organizationId == organizationId
    ).order_by(Alert.createdAt.desc()).all()

@router.patch("/{alert_id}/read")
def mark_read(alert_id: str, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if alert:
        alert.isRead = True
        db.commit()
    return {"message": "Alert marked as read"}