from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import (
    Asset, WorkOrder, Alert, AlertTypeEnum, SeverityEnum,
    MaintenanceLog, PartsUsed, PartsInventory,
)
from pydantic import BaseModel
from typing import Optional
import anthropic
import os
import uuid
from datetime import datetime

router = APIRouter()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

class AIAnalysisRequest(BaseModel):
    organizationId: str
    assetId: Optional[str] = None


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

class TicketAnalysisRequest(BaseModel):
    ticket_id: str
    asset: str
    client: str
    facility: str
    priority: str
    status: str
    technician: Optional[str] = None
    fault: Optional[str] = None


def _asset_history(db: Session, asset_id: str, exclude_wo: str) -> str:
    """Every previous job on this asset, with the parts actually fitted.

    The analysis used to reason from one fault description. It had no knowledge
    of which interventions were tried or what was replaced, which caps
    recommendation quality regardless of model. Three capacitors on one asset in
    eighteen months is not a capacitor problem — it is a supply voltage problem,
    and that pattern is invisible without parts history.
    """
    rows = (
        db.query(WorkOrder)
        .filter(WorkOrder.assetId == asset_id, WorkOrder.id != exclude_wo)
        .order_by(WorkOrder.createdAt.desc())
        .limit(20)
        .all()
    )
    if not rows:
        return "No previous service records for this asset."

    lines = []
    for w in rows:
        date = w.createdAt.strftime("%Y-%m-%d") if w.createdAt else "unknown date"
        lines.append(f"- {date} [{w.priority}] {w.title}: {w.description or 'no description'}")

        log = db.query(MaintenanceLog).filter(MaintenanceLog.workOrderId == w.id).first()
        if not log:
            continue
        if log.notes:
            lines.append(f"    Work done: {log.notes}")
        if log.partsUsedDeclared is False:
            lines.append("    Parts: none needed (declared)")
            continue

        parts = db.query(PartsUsed).filter(PartsUsed.maintenanceLogId == log.id).all()
        for p in parts:
            name = p.partNameRaw
            if p.partId:
                cat = db.query(PartsInventory).filter(PartsInventory.id == p.partId).first()
                name = cat.name if cat else name
            lines.append(f"    Part fitted: {name} x{p.quantityUsed} ({p.source or 'source not recorded'})")

    return "\n".join(lines)


@router.post("/analyze-ticket")
def analyze_ticket(request: TicketAnalysisRequest, db: Session = Depends(get_db)):
    wo = db.query(WorkOrder).filter(WorkOrder.id == request.ticket_id).first()

    history = "No previous service records for this asset."
    if wo and wo.assetId:
        history = _asset_history(db, wo.assetId, wo.id)

    prompt = f"""You are an expert HVAC and field service maintenance engineer
working in Lagos, Nigeria. Mains supply is unstable, generator changeover is
common, and counterfeit or refurbished components are widespread in the parts
market. Take that operating context into account.

Analyze this service ticket:

Ticket ID: {request.ticket_id}
Client: {request.client}
Facility: {request.facility}
Asset: {request.asset}
Priority: {request.priority}
Status: {request.status}
Assigned Technician: {request.technician or 'Unassigned'}
Fault Description: {request.fault or 'No fault description provided'}

SERVICE HISTORY FOR THIS ASSET (previous jobs, work done, and parts fitted):
{history}

Provide:
1. Most likely root cause. If the history shows the same component replaced more
   than once, say so explicitly and treat repeat replacement as a symptom of an
   underlying cause rather than a recurring coincidence.
2. Recommended immediate actions for the technician, in the order he should do them.
3. Parts and tools to bring on site. Be specific about sizes and ratings where
   the asset type allows it.
4. Preventive measures to avoid recurrence.

If the service history is empty, say so plainly and base the analysis on the
fault description alone rather than inventing history.

Be specific and practical. Write for a technician who will read this on a phone
at the gate before he goes in."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )

    return {"analysis": message.content[0].text}