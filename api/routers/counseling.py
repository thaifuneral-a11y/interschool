"""api/routers/counseling.py"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from api.core.database import get_db
from api.core.dependencies import get_current_user, TokenData, CounselorUp, TeacherUp
from api.models.core import CounselingReferral, CounselingSession, CounselingFollowup, CaseStatus
from api.schemas.all import (
    ReferralCreate, ReferralUpdate, ReferralOut,
    SessionCreate, SessionOut, FollowupCreate, FollowupOut, SuccessResponse
)

router = APIRouter(prefix="/counseling")


@router.post("/referrals", response_model=ReferralOut, status_code=201)
async def create_referral(
    body: ReferralCreate,
    token_data: TokenData = Depends(TeacherUp),
    db: AsyncSession = Depends(get_db),
):
    ref = CounselingReferral(
        school_id=token_data.school_id,
        referred_by_id=token_data.user_id,
        **body.model_dump(),
    )
    db.add(ref)
    await db.commit()
    await db.refresh(ref)
    return ReferralOut.model_validate(ref)


@router.get("/referrals", response_model=list[ReferralOut])
async def list_referrals(
    status: Optional[CaseStatus] = None,
    counselor_id: Optional[str] = None,
    token_data: TokenData = Depends(CounselorUp),
    db: AsyncSession = Depends(get_db),
):
    q = select(CounselingReferral).where(CounselingReferral.school_id == token_data.school_id)
    if status:
        q = q.where(CounselingReferral.status == status)
    if counselor_id:
        q = q.where(CounselingReferral.counselor_id == counselor_id)
    result = await db.execute(q.order_by(CounselingReferral.created_at.desc()))
    return [ReferralOut.model_validate(r) for r in result.scalars().all()]


@router.put("/referrals/{ref_id}", response_model=ReferralOut)
async def update_referral(
    ref_id: str,
    body: ReferralUpdate,
    token_data: TokenData = Depends(CounselorUp),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CounselingReferral).where(CounselingReferral.id == ref_id))
    ref = result.scalar_one_or_none()
    if not ref:
        raise HTTPException(404, "Referral not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(ref, k, v)
    from datetime import datetime, timezone
    if body.status in (CaseStatus.CLOSED, CaseStatus.ARCHIVED):
        ref.closed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(ref)
    return ReferralOut.model_validate(ref)


@router.post("/sessions", response_model=SessionOut, status_code=201)
async def create_session(
    body: SessionCreate,
    token_data: TokenData = Depends(CounselorUp),
    db: AsyncSession = Depends(get_db),
):
    session = CounselingSession(counselor_id=token_data.user_id, **body.model_dump())
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return SessionOut.model_validate(session)


@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions(
    referral_id: Optional[str] = None,
    token_data: TokenData = Depends(CounselorUp),
    db: AsyncSession = Depends(get_db),
):
    q = select(CounselingSession)
    if referral_id:
        q = q.where(CounselingSession.referral_id == referral_id)
    result = await db.execute(q.order_by(CounselingSession.session_date.desc()))
    return [SessionOut.model_validate(s) for s in result.scalars().all()]


@router.post("/followups", response_model=FollowupOut, status_code=201)
async def create_followup(
    body: FollowupCreate,
    token_data: TokenData = Depends(CounselorUp),
    db: AsyncSession = Depends(get_db),
):
    fu = CounselingFollowup(**body.model_dump())
    db.add(fu)
    await db.commit()
    await db.refresh(fu)
    return FollowupOut.model_validate(fu)


@router.get("/followups", response_model=list[FollowupOut])
async def list_followups(
    assigned_to_me: bool = False,
    token_data: TokenData = Depends(CounselorUp),
    db: AsyncSession = Depends(get_db),
):
    q = select(CounselingFollowup).where(CounselingFollowup.is_completed == False)
    if assigned_to_me:
        q = q.where(CounselingFollowup.assigned_to_id == token_data.user_id)
    result = await db.execute(q.order_by(CounselingFollowup.due_date))
    return [FollowupOut.model_validate(f) for f in result.scalars().all()]


@router.put("/followups/{fu_id}/complete", response_model=SuccessResponse)
async def complete_followup(
    fu_id: str,
    token_data: TokenData = Depends(CounselorUp),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timezone
    result = await db.execute(select(CounselingFollowup).where(CounselingFollowup.id == fu_id))
    fu = result.scalar_one_or_none()
    if not fu:
        raise HTTPException(404, "Follow-up not found")
    fu.is_completed = True
    fu.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    return SuccessResponse(message="Follow-up marked complete")


@router.get("/dashboard")
async def counseling_dashboard(
    token_data: TokenData = Depends(CounselorUp),
    db: AsyncSession = Depends(get_db),
):
    total_open = await db.execute(
        select(func.count(CounselingReferral.id)).where(
            CounselingReferral.school_id == token_data.school_id,
            CounselingReferral.status.in_([CaseStatus.OPEN, CaseStatus.ACTIVE]),
        )
    )
    overdue_fu = await db.execute(
        select(func.count(CounselingFollowup.id)).where(
            CounselingFollowup.is_completed == False,
            CounselingFollowup.assigned_to_id == token_data.user_id,
        )
    )
    return {
        "open_cases": total_open.scalar(),
        "overdue_followups": overdue_fu.scalar(),
    }
