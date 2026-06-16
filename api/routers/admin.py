"""api/routers/admin.py"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from api.core.database import get_db
from api.core.dependencies import get_current_user, TokenData, SuperAdminOnly
from api.models.core import School, User, SchoolUser, Student
from api.schemas.all import SchoolCreate, SchoolOut, SuccessResponse

router = APIRouter(prefix="/admin")


@router.get("/schools", response_model=list[SchoolOut])
async def list_schools(
    token_data: TokenData = Depends(SuperAdminOnly),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(School).order_by(School.name))
    return [SchoolOut.model_validate(s) for s in result.scalars().all()]


@router.post("/schools", response_model=SchoolOut, status_code=201)
async def create_school(
    body: SchoolCreate,
    token_data: TokenData = Depends(SuperAdminOnly),
    db: AsyncSession = Depends(get_db),
):
    school = School(**body.model_dump())
    db.add(school)
    await db.commit()
    await db.refresh(school)
    return SchoolOut.model_validate(school)


@router.get("/schools/{school_id}/stats")
async def school_stats(
    school_id: str,
    token_data: TokenData = Depends(SuperAdminOnly),
    db: AsyncSession = Depends(get_db),
):
    students = await db.execute(
        select(func.count(Student.id)).where(Student.school_id == school_id, Student.is_active == True)
    )
    users = await db.execute(
        select(func.count(SchoolUser.id)).where(SchoolUser.school_id == school_id, SchoolUser.is_active == True)
    )
    return {"students": students.scalar(), "users": users.scalar()}


@router.put("/schools/{school_id}/toggle", response_model=SuccessResponse)
async def toggle_school(
    school_id: str,
    token_data: TokenData = Depends(SuperAdminOnly),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(School).where(School.id == school_id))
    school = result.scalar_one_or_none()
    if not school:
        raise HTTPException(404, "School not found")
    school.is_active = not school.is_active
    await db.commit()
    return SuccessResponse(message=f"School {'activated' if school.is_active else 'deactivated'}")
