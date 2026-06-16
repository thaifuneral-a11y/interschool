"""api/routers/parents.py"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.core.database import get_db
from api.core.dependencies import get_current_user, TokenData, ParentOnly
from api.models.core import (
    StudentParent, AttendanceRecord, SchoolAnnouncement,
    ParentTeacherMeeting, AbsenceExplanation, NotificationLog
)
from api.schemas.all import (
    AttendanceOut, AnnouncementOut, MeetingBookRequest, MeetingOut,
    AbsenceExplanationCreate, SuccessResponse, NotificationOut
)

router = APIRouter(prefix="/parent")


@router.get("/children")
async def get_my_children(
    token_data: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(StudentParent).where(StudentParent.user_id == token_data.user_id)
    )
    return [{"student_id": str(sp.student_id), "relationship": sp.relationship_type} for sp in result.scalars().all()]


@router.get("/children/{student_id}/attendance", response_model=list[AttendanceOut])
async def child_attendance(
    student_id: str,
    token_data: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify parent-child link
    link = await db.execute(
        select(StudentParent).where(
            StudentParent.user_id == token_data.user_id,
            StudentParent.student_id == student_id,
        )
    )
    if not link.scalar_one_or_none():
        raise HTTPException(403, "Not linked to this student")
    result = await db.execute(
        select(AttendanceRecord)
        .where(AttendanceRecord.student_id == student_id)
        .order_by(AttendanceRecord.date.desc())
        .limit(90)
    )
    return [AttendanceOut.model_validate(r) for r in result.scalars().all()]


@router.post("/absence-explanations", response_model=SuccessResponse)
async def submit_explanation(
    body: AbsenceExplanationCreate,
    token_data: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    exp = AbsenceExplanation(
        attendance_id=body.attendance_id,
        submitted_by_id=token_data.user_id,
        reason=body.reason,
    )
    db.add(exp)
    await db.commit()
    return SuccessResponse(message="Explanation submitted")


@router.get("/announcements", response_model=list[AnnouncementOut])
async def get_announcements(
    token_data: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime
    result = await db.execute(
        select(SchoolAnnouncement).where(
            SchoolAnnouncement.school_id == token_data.school_id,
            SchoolAnnouncement.is_published == True,
            SchoolAnnouncement.audience.in_(["all", "parents"]),
        ).order_by(SchoolAnnouncement.created_at.desc()).limit(20)
    )
    return [AnnouncementOut.model_validate(a) for a in result.scalars().all()]


@router.post("/meetings/book", response_model=MeetingOut, status_code=201)
async def book_meeting(
    body: MeetingBookRequest,
    token_data: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    meeting = ParentTeacherMeeting(
        school_id=token_data.school_id,
        parent_id=token_data.user_id,
        **body.model_dump(),
    )
    db.add(meeting)
    await db.commit()
    await db.refresh(meeting)
    return MeetingOut.model_validate(meeting)


@router.get("/meetings", response_model=list[MeetingOut])
async def my_meetings(
    token_data: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ParentTeacherMeeting)
        .where(ParentTeacherMeeting.parent_id == token_data.user_id)
        .order_by(ParentTeacherMeeting.scheduled_at)
    )
    return [MeetingOut.model_validate(m) for m in result.scalars().all()]


@router.delete("/meetings/{meeting_id}", response_model=SuccessResponse)
async def cancel_meeting(
    meeting_id: str,
    token_data: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ParentTeacherMeeting).where(
            ParentTeacherMeeting.id == meeting_id,
            ParentTeacherMeeting.parent_id == token_data.user_id,
        )
    )
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(404, "Meeting not found")
    meeting.status = "cancelled"
    await db.commit()
    return SuccessResponse(message="Meeting cancelled")
