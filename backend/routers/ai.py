from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Asset, WorkOrder, Alert, AlertTypeEnum, SeverityEnum
from pydantic import BaseModel
import anthropic
import os
import uuid
from datetime import datetime

router = APIRouter()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

class AIAnalysisRequest(BaseModel):
    organizationId: str
    assetId: Optional[str] = None

from typing import Optional

@router.post("/analyze")
def analyze_assets(request: AIAnalysisRequest, db: Session = Depends(get_db)):
    assets = db.query(Asset).filter(Asset.organizationId == request.organizationId).all()
    workorders = db.query(WorkOrder).filter(WorkOrder.organizationId == request.organizationId).all()

    asset_summary = [
        f"Asset: {a.name}, Category: {a.category}, Status: {a.status}, Warranty: {a.warrantyExpiry}"
        for a in assets
    ]
    wo_summary = [
        f"WorkOrder: {w.title}, Priority: {w.priority}, Status: {w.status}, Due: {w.dueDate}"
        for w in workorders
    ]

    prompt = f"""You are an AI maintenance expert for EquipTrack AI.
Analyze the following assets and work orders and identify:
1. Assets at risk of failure
2. Overdue or high-priority maintenance needs
3. Specific recommended actions

Assets:
{chr(10).join(asset_summary)}

Work Orders:
{chr(10).join(wo_summary)}

Respond in JSON format:
{{
  "risks": [
    {{"assetName": "...", "risk": "...", "severity": "LOW|MEDIUM|HIGH|CRITICAL", "action": "..."}}
  ],
  "summary": "..."
}}"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )

    return {"analysis": message.content[0].text}

@router.post("/generate-alerts")
def generate_alerts(organizationId: str, db: Session = Depends(get_db)):
    from datetime import timezone, timedelta
    now = datetime.now()
    soon = now + timedelta(days=30)
    
    assets = db.query(Asset).filter(
        Asset.organizationId == organizationId,
        Asset.warrantyExpiry != None,
        Asset.warrantyExpiry <= soon
    ).all()

    alerts_created = []
    for asset in assets:
        alert = Alert(
            id=str(uuid.uuid4()),
            type=AlertTypeEnum.WARRANTY_EXPIRY,
            message=f"Warranty for {asset.name} expires on {asset.warrantyExpiry.strftime('%Y-%m-%d')}",
            severity=SeverityEnum.HIGH,
            isRead=False,
            organizationId=organizationId,
            assetId=asset.id,
            createdAt=now
        )
        db.add(alert)
        alerts_created.append(asset.name)

    db.commit()
    return {"alerts_created": len(alerts_created), "assets": alerts_created}