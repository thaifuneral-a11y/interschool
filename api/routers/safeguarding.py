"""api/routers/safeguarding.py"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from api.core.database import get_db
from api.core.dependencies import get_current_user, TokenData, CounselorUp, TeacherUp
from api.models.core import (
    SafeguardingIncident, IncidentNote, SafeguardingEscalation,
    RiskLevel, IncidentStatus, UserRole
)
from api.schemas.all import (
    IncidentCreate, IncidentUpdate, IncidentOut,
    IncidentNoteCreate, EscalationCreate, SuccessResponse
)
from api.services.notifications import send_critical_alert

router = APIRouter(prefix="/safeguarding")


@router.post("/incidents", response_model=IncidentOut, status_code=201)
async def report_incident(
    body: IncidentCreate,
    background_tasks: BackgroundTasks,
    token_data: TokenData = Depends(TeacherUp),
    db: AsyncSession = Depends(get_db),
):
    incident = SafeguardingIncident(
        school_id=token_data.school_id,
        reporter_id=token_data.user_id,
        **body.model_dump(),
    )
    db.add(incident)
    await db.commit()
    await db.refresh(incident)

    if incident.risk_level == RiskLevel.CRITICAL:
        background_tasks.add_task(
            send_critical_alert,
            school_id=str(token_data.school_id),
            incident_id=str(incident.id),
            student_id=str(body.student_id),
        )

    return IncidentOut.model_validate(incident)


@router.get("/incidents", response_model=list[IncidentOut])
async def list_incidents(
    risk_level: Optional[RiskLevel] = None,
    status: Optional[IncidentStatus] = None,
    token_data: TokenData = Depends(CounselorUp),
    db: AsyncSession = Depends(get_db),
):
    q = select(SafeguardingIncident).where(
        SafeguardingIncident.school_id == token_data.school_id
    )
    if risk_level:
        q = q.where(SafeguardingIncident.risk_level == risk_level)
    if status:
        q = q.where(SafeguardingIncident.status == status)
    result = await db.execute(q.order_by(SafeguardingIncident.created_at.desc()))
    return [IncidentOut.model_validate(i) for i in result.scalars().all()]


@router.get("/incidents/{incident_id}", response_model=IncidentOut)
async def get_incident(
    incident_id: str,
    token_data: TokenData = Depends(CounselorUp),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SafeguardingIncident).where(
            SafeguardingIncident.id == incident_id,
            SafeguardingIncident.school_id == token_data.school_id,
        )
    )
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(404, "Incident not found")
    return IncidentOut.model_validate(incident)


@router.put("/incidents/{incident_id}/risk-level", response_model=IncidentOut)
async def update_risk_level(
    incident_id: str,
    risk_level: RiskLevel,
    background_tasks: BackgroundTasks,
    token_data: TokenData = Depends(CounselorUp),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SafeguardingIncident).where(SafeguardingIncident.id == incident_id)
    )
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(404, "Incident not found")
    incident.risk_level = risk_level
    await db.commit()
    await db.refresh(incident)
    if risk_level == RiskLevel.CRITICAL:
        background_tasks.add_task(
            send_critical_alert, str(token_data.school_id), incident_id, str(incident.student_id)
        )
    return IncidentOut.model_validate(incident)


@router.post("/incidents/{incident_id}/escalate", response_model=SuccessResponse)
async def escalate_incident(
    incident_id: str,
    body: EscalationCreate,
    token_data: TokenData = Depends(CounselorUp),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SafeguardingIncident).where(SafeguardingIncident.id == incident_id)
    )
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(404, "Incident not found")
    incident.is_escalated = True
    incident.escalated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    incident.status = IncidentStatus.ESCALATED
    db.add(SafeguardingEscalation(
        incident_id=incident_id,
        escalated_by_id=token_data.user_id,
        **body.model_dump(),
    ))
    await db.commit()
    return SuccessResponse(message="Incident escalated")


@router.post("/incidents/{incident_id}/notes", response_model=SuccessResponse)
async def add_note(
    incident_id: str,
    body: IncidentNoteCreate,
    token_data: TokenData = Depends(CounselorUp),
    db: AsyncSession = Depends(get_db),
):
    note = IncidentNote(
        incident_id=incident_id,
        author_id=token_data.user_id,
        content=body.content,
    )
    db.add(note)
    await db.commit()
    return SuccessResponse(message="Note added")


@router.post("/incidents/{incident_id}/close", response_model=SuccessResponse)
async def close_incident(
    incident_id: str,
    resolution_notes: str,
    token_data: TokenData = Depends(CounselorUp),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SafeguardingIncident).where(SafeguardingIncident.id == incident_id)
    )
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(404, "Incident not found")
    incident.status = IncidentStatus.RESOLVED
    incident.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None)
    incident.resolution_notes = resolution_notes
    await db.commit()
    return SuccessResponse(message="Incident closed")
