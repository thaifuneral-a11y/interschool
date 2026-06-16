"""api/routers/attendance.py — Attendance management"""

from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from api.core.database import get_db
from api.core.dependencies import get_current_user, TokenData, TeacherUp, CounselorUp
from api.models.core import (
    AttendanceRecord, AbsenceExplanation, Student, AttendanceStatus
)
from api.schemas.all import (
    AttendanceBulkRequest, AttendanceOut, AbsenceExplanationCreate,
    AbsenceExplanationReview, AttendanceStatsOut, SuccessResponse
)

router = APIRouter(prefix="/attendance")


@router.get("", response_model=list[AttendanceOut])
async def get_attendance_roll(
    date_str: date = Query(..., alias="date"),
    class_name: Optional[str] = None,
    grade_level: Optional[str] = None,
    token_data: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(AttendanceRecord)
        .join(Student, AttendanceRecord.student_id == Student.id)
        .where(
            AttendanceRecord.school_id == token_data.school_id,
            AttendanceRecord.date == date_str,
        )
    )
    if class_name:
        q = q.where(Student.class_name == class_name)
    if grade_level:
        q = q.where(Student.grade_level == grade_level)
    result = await db.execute(q.order_by(Student.full_name))
    return [AttendanceOut.model_validate(r) for r in result.scalars().all()]


@router.post("/bulk", response_model=SuccessResponse, status_code=201)
async def bulk_mark_attendance(
    body: AttendanceBulkRequest,
    token_data: TokenData = Depends(TeacherUp),
    db: AsyncSession = Depends(get_db),
):
    for item in body.records:
        # Upsert: update if exists
        result = await db.execute(
            select(AttendanceRecord).where(
                AttendanceRecord.student_id == item.student_id,
                AttendanceRecord.date == body.date,
            )
        )
        record = result.scalar_one_or_none()
        if record:
            record.status = item.status
            record.check_in_time = item.check_in_time
            record.notes = item.notes
            record.marked_by_id = token_data.user_id
        else:
            record = AttendanceRecord(
                school_id=token_data.school_id,
                student_id=item.student_id,
                date=body.date,
                status=item.status,
                check_in_time=item.check_in_time,
                notes=item.notes,
                marked_by_id=token_data.user_id,
            )
            db.add(record)
    await db.commit()
    return SuccessResponse(message=f"Marked {len(body.records)} attendance records")


@router.put("/{record_id}", response_model=AttendanceOut)
async def update_attendance(
    record_id: str,
    status: AttendanceStatus,
    notes: Optional[str] = None,
    token_data: TokenData = Depends(TeacherUp),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.id == record_id,
            AttendanceRecord.school_id == token_data.school_id,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    record.status = status
    record.notes = notes
    await db.commit()
    await db.refresh(record)
    return AttendanceOut.model_validate(record)


@router.get("/stats", response_model=AttendanceStatsOut)
async def get_attendance_stats(
    date_str: date = Query(default=date.today(), alias="date"),
    token_data: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    total_q = await db.execute(
        select(func.count(Student.id)).where(
            Student.school_id == token_data.school_id, Student.is_active == True
        )
    )
    total = total_q.scalar() or 0

    status_q = await db.execute(
        select(AttendanceRecord.status, func.count(AttendanceRecord.id))
        .where(
            AttendanceRecord.school_id == token_data.school_id,
            AttendanceRecord.date == date_str,
        )
        .group_by(AttendanceRecord.status)
    )
    counts = {row[0]: row[1] for row in status_q.all()}

    present = counts.get(AttendanceStatus.PRESENT, 0) + counts.get(AttendanceStatus.LATE, 0)
    absent = counts.get(AttendanceStatus.ABSENT, 0)
    late = counts.get(AttendanceStatus.LATE, 0)
    excused = counts.get(AttendanceStatus.EXCUSED, 0)
    rate = (present / total * 100) if total > 0 else 0.0

    return AttendanceStatsOut(
        date=date_str,
        total_students=total,
        present=present,
        absent=absent,
        late=late,
        excused=excused,
        attendance_rate=round(rate, 2),
    )


@router.get("/student/{student_id}", response_model=list[AttendanceOut])
async def get_student_attendance(
    student_id: str,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    token_data: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(AttendanceRecord).where(
        AttendanceRecord.student_id == student_id,
        AttendanceRecord.school_id == token_data.school_id,
    )
    if from_date:
        q = q.where(AttendanceRecord.date >= from_date)
    if to_date:
        q = q.where(AttendanceRecord.date <= to_date)
    result = await db.execute(q.order_by(AttendanceRecord.date.desc()))
    return [AttendanceOut.model_validate(r) for r in result.scalars().all()]


# ── Absence Explanations ──────────────────────────────────────────────────────
@router.post("/absence-explanations", response_model=SuccessResponse, status_code=201)
async def submit_absence_explanation(
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
    return SuccessResponse(message="Absence explanation submitted")


@router.put("/absence-explanations/{exp_id}", response_model=SuccessResponse)
async def review_absence_explanation(
    exp_id: str,
    body: AbsenceExplanationReview,
    token_data: TokenData = Depends(TeacherUp),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AbsenceExplanation).where(AbsenceExplanation.id == exp_id))
    exp = result.scalar_one_or_none()
    if not exp:
        raise HTTPException(status_code=404, detail="Explanation not found")
    from datetime import datetime, timezone
    exp.status = body.status
    exp.review_notes = body.review_notes
    exp.reviewed_by_id = token_data.user_id
    exp.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    if body.status == "approved":
        att_result = await db.execute(
            select(AttendanceRecord).where(AttendanceRecord.id == exp.attendance_id)
        )
        att = att_result.scalar_one_or_none()
        if att:
            att.is_excused = True
    await db.commit()
    return SuccessResponse(message=f"Explanation {body.status}")
