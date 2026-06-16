"""api/services/audit.py — Append-only audit logging"""

from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from api.models.core import AuditLog


async def log_action(
    db: AsyncSession,
    user_id: str,
    school_id: str,
    action: str,
    resource_type: str,
    resource_id: str = None,
    old_value: dict = None,
    new_value: dict = None,
    ip: str = None,
    user_agent: str = None,
):
    """Write an immutable audit record. Never update or delete audit_logs."""
    log = AuditLog(
        user_id=user_id,
        school_id=school_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        old_value=old_value,
        new_value=new_value,
        ip_address=ip,
        user_agent=user_agent,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(log)
    # Note: commit is handled by the router's db session lifecycle
