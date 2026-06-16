"""api/routers/dashboard.py"""

from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case

from api.core.database import get_db
from api.core.dependencies import get_current_user, TokenData
from api.models.core import (
    Student, AttendanceRecord, AttendanceStatus,
    CounselingReferral, SafeguardingIncident,
    CaseStatus, IncidentStatus, RiskLevel
)
from api.schemas.all import DashboardOverview, AttendanceTrendPoint, AtRiskStudent

router = APIRouter(prefix="/dashboard")


@router.get("/overview", response_model=DashboardOverview)
async def overview(
    token_data: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    school_id = token_data.school_id

    # Total students
    total_q = await db.execute(
        select(func.count(Student.id)).where(
            Student.school_id == school_id, Student.is_active == True
        )
    )
    total = total_q.scalar() or 1

    # Today's attendance
    att_q = await db.execute(
        select(AttendanceRecord.status, func.count(AttendanceRecord.id))
        .where(AttendanceRecord.school_id == school_id, AttendanceRecord.date == today)
        .group_by(AttendanceRecord.status)
    )
    counts = {r[0]: r[1] for r in att_q.all()}
    present_today = counts.get(AttendanceStatus.PRESENT, 0) + counts.get(AttendanceStatus.LATE, 0)
    att_today_pct = round(present_today / total * 100, 2)

    # Weekly avg
    week_ago = today - timedelta(days=7)
    weekly_q = await db.execute(
        select(AttendanceRecord.date, func.count(AttendanceRecord.id))
        .where(
            AttendanceRecord.school_id == school_id,
            AttendanceRecord.date >= week_ago,
            AttendanceRecord.status.in_([AttendanceStatus.PRESENT, AttendanceStatus.LATE]),
        )
        .group_by(AttendanceRecord.date)
    )
    weekly_rows = weekly_q.all()
    weekly_avg = round(sum(r[1] for r in weekly_rows) / max(len(weekly_rows), 1) / total * 100, 2)

    # Chronic absentees (absent 3+ days in last 14)
    two_weeks_ago = today - timedelta(days=14)
    chronic_q = await db.execute(
        select(AttendanceRecord.student_id, func.count(AttendanceRecord.id).label("cnt"))
        .where(
            AttendanceRecord.school_id == school_id,
            AttendanceRecord.date >= two_weeks_ago,
            AttendanceRecord.status == AttendanceStatus.ABSENT,
            AttendanceRecord.is_excused == False,
        )
        .group_by(AttendanceRecord.student_id)
        .having(func.count(AttendanceRecord.id) >= 3)
    )
    chronic = len(chronic_q.all())

    # Open counseling
    counsel_q = await db.execute(
        select(func.count(CounselingReferral.id)).where(
            CounselingReferral.school_id == school_id,
            CounselingReferral.status.in_([CaseStatus.OPEN, CaseStatus.ACTIVE]),
        )
    )

    # Open safeguarding
    safe_q = await db.execute(
        select(func.count(SafeguardingIncident.id)).where(
            SafeguardingIncident.school_id == school_id,
            SafeguardingIncident.status.in_([IncidentStatus.OPEN, IncidentStatus.UNDER_REVIEW, IncidentStatus.ESCALATED]),
        )
    )
    critical_q = await db.execute(
        select(func.count(SafeguardingIncident.id)).where(
            SafeguardingIncident.school_id == school_id,
            SafeguardingIncident.risk_level == RiskLevel.CRITICAL,
            SafeguardingIncident.status != IncidentStatus.RESOLVED,
        )
    )

    return DashboardOverview(
        attendance_today_pct=att_today_pct,
        attendance_weekly_avg=weekly_avg,
        chronic_absentees=chronic,
        open_counseling_cases=counsel_q.scalar() or 0,
        open_safeguarding_incidents=safe_q.scalar() or 0,
        critical_incidents=critical_q.scalar() or 0,
        total_students=total,
        at_risk_count=chronic,
    )


@router.get("/attendance-trend", response_model=list[AttendanceTrendPoint])
async def attendance_trend(
    days: int = 30,
    token_data: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    start = date.today() - timedelta(days=days)
    total_q = await db.execute(
        select(func.count(Student.id)).where(
            Student.school_id == token_data.school_id, Student.is_active == True
        )
    )
    total = total_q.scalar() or 1

    q = await db.execute(
        select(
            AttendanceRecord.date,
            func.count(AttendanceRecord.id).label("total"),
            func.sum(
                case(
                    (AttendanceRecord.status.in_([AttendanceStatus.PRESENT, AttendanceStatus.LATE]), 1),
                    else_=0,
                )
            ).label("present"),
        )
        .where(
            AttendanceRecord.school_id == token_data.school_id,
            AttendanceRecord.date >= start,
        )
        .group_by(AttendanceRecord.date)
        .order_by(AttendanceRecord.date)
    )
    rows = q.all()
    return [
        AttendanceTrendPoint(
            date=r[0],
            rate=round((r[2] or 0) / total * 100, 2),
            present=r[2] or 0,
            absent=r[1] - (r[2] or 0),
        )
        for r in rows
    ]


@router.get("/at-risk-students", response_model=list[AtRiskStudent])
async def at_risk_students(
    token_data: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    school_id = token_data.school_id
    three_days_ago = date.today() - timedelta(days=3)

    # Students with 3+ consecutive absences
    absent_q = await db.execute(
        select(AttendanceRecord.student_id, func.count(AttendanceRecord.id).label("cnt"))
        .where(
            AttendanceRecord.school_id == school_id,
            AttendanceRecord.date >= three_days_ago,
            AttendanceRecord.status == AttendanceStatus.ABSENT,
        )
        .group_by(AttendanceRecord.student_id)
        .having(func.count(AttendanceRecord.id) >= 3)
    )
    at_risk_ids = {str(r[0]): r[1] for r in absent_q.all()}

    if not at_risk_ids:
        return []

    students_q = await db.execute(
        select(Student).where(Student.id.in_(list(at_risk_ids.keys())))
    )
    students = students_q.scalars().all()

    result = []
    for s in students:
        # Check open counseling
        c_q = await db.execute(
            select(func.count(CounselingReferral.id)).where(
                CounselingReferral.student_id == s.id,
                CounselingReferral.status.in_([CaseStatus.OPEN, CaseStatus.ACTIVE]),
            )
        )
        # Check open safeguarding
        sg_q = await db.execute(
            select(func.count(SafeguardingIncident.id)).where(
                SafeguardingIncident.student_id == s.id,
                SafeguardingIncident.status != IncidentStatus.RESOLVED,
            )
        )
        result.append(
            AtRiskStudent(
                student_id=s.id,
                full_name=s.full_name,
                grade_level=s.grade_level,
                class_name=s.class_name,
                consecutive_absences=at_risk_ids.get(str(s.id), 0),
                open_counseling=c_q.scalar() > 0,
                open_safeguarding=sg_q.scalar() > 0,
            )
        )
    return result
