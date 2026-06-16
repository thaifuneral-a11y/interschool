"""api/routers/students.py — Student management endpoints"""

import csv
import io
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from api.core.database import get_db
from api.core.dependencies import get_current_user, TokenData, CounselorUp, TeacherUp
from api.models.core import Student, EmergencyContact, MedicalSummary, StudentParent, User
from api.schemas.all import (
    StudentCreate, StudentUpdate, StudentOut, EmergencyContactCreate, EmergencyContactOut,
    MedicalSummaryUpdate, MedicalSummaryOut, PaginatedResponse, SuccessResponse
)

router = APIRouter(prefix="/students")


@router.get("", response_model=PaginatedResponse[StudentOut])
async def list_students(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    q: Optional[str] = None,
    grade_level: Optional[str] = None,
    class_name: Optional[str] = None,
    is_active: Optional[bool] = True,
    token_data: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Student).where(Student.school_id == token_data.school_id)
    if is_active is not None:
        query = query.where(Student.is_active == is_active)
    if q:
        query = query.where(
            or_(Student.full_name.ilike(f"%{q}%"), Student.student_number.ilike(f"%{q}%"))
        )
    if grade_level:
        query = query.where(Student.grade_level == grade_level)
    if class_name:
        query = query.where(Student.class_name == class_name)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar()

    query = query.offset((page - 1) * per_page).limit(per_page).order_by(Student.full_name)
    result = await db.execute(query)
    students = result.scalars().all()

    return PaginatedResponse(
        items=[StudentOut.model_validate(s) for s in students],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page,
    )


@router.post("", response_model=StudentOut, status_code=201)
async def create_student(
    body: StudentCreate,
    token_data: TokenData = Depends(TeacherUp),
    db: AsyncSession = Depends(get_db),
):
    student = Student(**body.model_dump(), school_id=token_data.school_id)
    db.add(student)
    await db.commit()
    await db.refresh(student)
    return StudentOut.model_validate(student)


@router.get("/{student_id}", response_model=StudentOut)
async def get_student(
    student_id: str,
    token_data: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Student).where(Student.id == student_id, Student.school_id == token_data.school_id)
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return StudentOut.model_validate(student)


@router.put("/{student_id}", response_model=StudentOut)
async def update_student(
    student_id: str,
    body: StudentUpdate,
    token_data: TokenData = Depends(TeacherUp),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Student).where(Student.id == student_id, Student.school_id == token_data.school_id)
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(student, k, v)
    await db.commit()
    await db.refresh(student)
    return StudentOut.model_validate(student)


@router.delete("/{student_id}", response_model=SuccessResponse)
async def deactivate_student(
    student_id: str,
    token_data: TokenData = Depends(TeacherUp),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Student).where(Student.id == student_id, Student.school_id == token_data.school_id)
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    student.is_active = False
    await db.commit()
    return SuccessResponse(message="Student deactivated")


# ── Emergency Contacts ────────────────────────────────────────────────────────
@router.get("/{student_id}/emergency-contacts", response_model=list[EmergencyContactOut])
async def get_emergency_contacts(
    student_id: str,
    token_data: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(EmergencyContact)
        .where(EmergencyContact.student_id == student_id)
        .order_by(EmergencyContact.priority)
    )
    return [EmergencyContactOut.model_validate(c) for c in result.scalars().all()]


@router.post("/{student_id}/emergency-contacts", response_model=EmergencyContactOut, status_code=201)
async def add_emergency_contact(
    student_id: str,
    body: EmergencyContactCreate,
    token_data: TokenData = Depends(TeacherUp),
    db: AsyncSession = Depends(get_db),
):
    contact = EmergencyContact(**body.model_dump(), student_id=student_id)
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return EmergencyContactOut.model_validate(contact)


# ── Medical Summary ───────────────────────────────────────────────────────────
@router.get("/{student_id}/medical", response_model=MedicalSummaryOut)
async def get_medical(
    student_id: str,
    token_data: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MedicalSummary).where(MedicalSummary.student_id == student_id)
    )
    med = result.scalar_one_or_none()
    if not med:
        raise HTTPException(status_code=404, detail="No medical record found")
    return MedicalSummaryOut.model_validate(med)


@router.put("/{student_id}/medical", response_model=MedicalSummaryOut)
async def upsert_medical(
    student_id: str,
    body: MedicalSummaryUpdate,
    token_data: TokenData = Depends(CounselorUp),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MedicalSummary).where(MedicalSummary.student_id == student_id)
    )
    med = result.scalar_one_or_none()
    if med:
        for k, v in body.model_dump(exclude_unset=True).items():
            setattr(med, k, v)
    else:
        med = MedicalSummary(**body.model_dump(), student_id=student_id)
        db.add(med)
    await db.commit()
    await db.refresh(med)
    return MedicalSummaryOut.model_validate(med)


# ── Bulk Upload ───────────────────────────────────────────────────────────────
@router.post("/bulk-upload", response_model=SuccessResponse)
async def bulk_upload_students(
    file: UploadFile = File(...),
    token_data: TokenData = Depends(TeacherUp),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
    created = 0
    for row in reader:
        student = Student(
            school_id=token_data.school_id,
            student_number=row.get("student_number", ""),
            full_name=row.get("full_name", ""),
            grade_level=row.get("grade_level"),
            class_name=row.get("class_name"),
            nationality=row.get("nationality"),
        )
        db.add(student)
        created += 1
    await db.commit()
    return SuccessResponse(message=f"Imported {created} students")
