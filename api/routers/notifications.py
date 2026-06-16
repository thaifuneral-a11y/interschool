"""api/routers/notifications.py"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from api.core.database import get_db
from api.core.dependencies import get_current_user, TokenData
from api.models.core import NotificationLog, PushToken, NotificationPreference, SchoolAnnouncement
from api.schemas.all import (
    NotificationOut, PushTokenRegister, BroadcastRequest, AnnouncementCreate,
    AnnouncementOut, SuccessResponse
)

router = APIRouter(prefix="/notifications")


@router.get("", response_model=list[NotificationOut])
async def get_notifications(
    limit: int = 50,
    unread_only: bool = False,
    token_data: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(NotificationLog).where(NotificationLog.recipient_id == token_data.user_id)
    if unread_only:
        q = q.where(NotificationLog.is_read == False)
    result = await db.execute(q.order_by(NotificationLog.created_at.desc()).limit(limit))
    return [NotificationOut.model_validate(n) for n in result.scalars().all()]


@router.put("/{notif_id}/read", response_model=SuccessResponse)
async def mark_read(
    notif_id: str,
    token_data: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timezone
    result = await db.execute(
        select(NotificationLog).where(
            NotificationLog.id == notif_id,
            NotificationLog.recipient_id == token_data.user_id,
        )
    )
    notif = result.scalar_one_or_none()
    if notif:
        notif.is_read = True
        notif.read_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()
    return SuccessResponse(message="Marked as read")


@router.put("/mark-all-read", response_model=SuccessResponse)
async def mark_all_read(
    token_data: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timezone
    from sqlalchemy import update
    await db.execute(
        update(NotificationLog)
        .where(NotificationLog.recipient_id == token_data.user_id, NotificationLog.is_read == False)
        .values(is_read=True, read_at=datetime.now(timezone.utc).replace(tzinfo=None))
    )
    await db.commit()
    return SuccessResponse(message="All notifications marked as read")


@router.post("/push-token", response_model=SuccessResponse)
async def register_push_token(
    body: PushTokenRegister,
    token_data: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(PushToken).where(PushToken.user_id == token_data.user_id, PushToken.token == body.token)
    )
    if not existing.scalar_one_or_none():
        db.add(PushToken(user_id=token_data.user_id, **body.model_dump()))
        await db.commit()
    return SuccessResponse(message="Push token registered")


@router.get("/preferences", response_model=list)
async def get_preferences(
    token_data: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == token_data.user_id)
    )
    return result.scalars().all()


@router.post("/broadcast", response_model=SuccessResponse)
async def broadcast(
    body: BroadcastRequest,
    token_data: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from api.models.core import UserRole
    if token_data.role not in (UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN, UserRole.PRINCIPAL):
        from fastapi import HTTPException
        raise HTTPException(403, "Not permitted")
    ann = SchoolAnnouncement(
        school_id=token_data.school_id,
        author_id=token_data.user_id,
        title=body.title,
        body=body.body,
        audience=body.audience,
        is_published=True,
    )
    db.add(ann)
    await db.commit()
    return SuccessResponse(message="Broadcast sent")
