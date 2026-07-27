"""Assignment notification.

An assignment that nobody receives is not an assignment.

Three layers:
  1. In-app badge      — no dependency, ships now. See GET /api/workorders/mine,
                         which sorts unaccepted jobs to the top with an age.
  2. WhatsApp on assign — this module. Posts to an n8n webhook which sends via
                         360dialog. Flagged OFF until Meta Business Verification
                         clears production access.
  3. Escalation         — Phase 1. Assigned but unaccepted past a priority-dependent
                         interval notifies the manager.

Failure here must never fail an assignment. Everything is wrapped and swallowed.
"""

import logging
import os
import threading
from typing import Optional

import requests

log = logging.getLogger(__name__)

# Off by default. Set to "true" only once 360dialog production access is live.
NOTIFY_ENABLED = os.getenv("NOTIFY_WHATSAPP_ENABLED", "false").lower() == "true"
N8N_WEBHOOK_URL = os.getenv("N8N_ASSIGNMENT_WEBHOOK_URL", "")
APP_URL = os.getenv("APP_PUBLIC_URL", "https://equiptrack-ai-dashboard.vercel.app")
TIMEOUT_SECONDS = 5


def _post(payload: dict) -> None:
    try:
        requests.post(N8N_WEBHOOK_URL, json=payload, timeout=TIMEOUT_SECONDS)
    except Exception as exc:  # noqa: BLE001 - notification must never break the write
        log.warning("Assignment notification failed: %s", exc)


def notify_assignment(work_order, technician, assigned_by: Optional[str] = None) -> None:
    """Fire-and-forget. Returns immediately whether or not the send succeeds."""
    if not NOTIFY_ENABLED or not N8N_WEBHOOK_URL:
        log.info(
            "WhatsApp notification skipped (flag off): job %s -> %s",
            work_order.id, technician.name,
        )
        return

    if not getattr(technician, "phone", None):
        log.warning("No phone on record for %s — cannot notify", technician.name)
        return

    payload = {
        "event": "workorder.assigned",
        "to": technician.phone,
        "technicianName": technician.name,
        "assignedBy": assigned_by,
        "workOrder": {
            "id": work_order.id,
            "shortId": work_order.id[:8].upper(),
            "title": work_order.title,
            "priority": work_order.priority.value if work_order.priority else None,
            "url": f"{APP_URL}/technician?job={work_order.id}",
        },
    }

    threading.Thread(target=_post, args=(payload,), daemon=True).start()