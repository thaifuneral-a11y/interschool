"""api/services/notifications.py — Push + in-app notifications"""

import json
from api.core.config import settings

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    if settings.FIREBASE_CREDENTIALS_JSON and not firebase_admin._apps:
        cred = credentials.Certificate(json.loads(settings.FIREBASE_CREDENTIALS_JSON))
        firebase_admin.initialize_app(cred)
    HAS_FIREBASE = True
except Exception:
    HAS_FIREBASE = False


async def send_push(tokens: list[str], title: str, body: str, data: dict = None):
    if not HAS_FIREBASE or not tokens:
        print(f"[PUSH] {title}: {body} → {tokens}")
        return
    from firebase_admin import messaging as fb
    message = fb.MulticastMessage(
        tokens=tokens,
        notification=fb.Notification(title=title, body=body),
        data={k: str(v) for k, v in (data or {}).items()},
    )
    fb.send_each_for_multicast(message)


async def send_critical_alert(school_id: str, incident_id: str, student_id: str):
    """Send immediate notification for CRITICAL safeguarding incidents."""
    # In production: fetch Principal + Admin push tokens from DB, then call send_push
    print(f"[CRITICAL ALERT] School: {school_id} | Incident: {incident_id} | Student: {student_id}")
    await send_push(
        tokens=[],  # Populated from DB in production
        title="⚠️ CRITICAL Safeguarding Incident",
        body="A critical safeguarding incident requires immediate attention.",
        data={"incident_id": incident_id, "student_id": student_id, "type": "safeguarding_critical"},
    )
