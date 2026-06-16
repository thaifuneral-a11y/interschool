"""api/schemas/all.py — Pydantic v2 request/response schemas"""

from __future__ import annotations
import uuid
from datetime import datetime, date
from typing import Optional, List, Generic, TypeVar
from pydantic import BaseModel, EmailStr, Field, ConfigDict

from api.models.core import (
    UserRole, AttendanceStatus, RiskLevel, CaseStatus, IncidentStatus
)

T = TypeVar("T")


# ── Common ────────────────────────────────────────────────────────────────────
class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    per_page: int
    pages: int


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


class SuccessResponse(BaseModel):
    message: str
    data: Optional[dict] = None


# ── Auth ──────────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    school_slug: str


class GoogleAuthRequest(BaseModel):
    id_token: str
    school_slug: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserOut"


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


class InviteUserRequest(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole


class AcceptInviteRequest(BaseModel):
    token: str
    password: str = Field(..., min_length=8)


# ── User ──────────────────────────────────────────────────────────────────────
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    phone: Optional[str]
    avatar_url: Optional[str]
    is_active: bool
    created_at: datetime


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None


# ── School ────────────────────────────────────────────────────────────────────
class SchoolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    country: str
    timezone: str
    logo_url: Optional[str]
    is_active: bool


class SchoolCreate(BaseModel):
    name: str
    slug: str
    country: str
    timezone: str = "UTC"


# ── Student ───────────────────────────────────────────────────────────────────
class StudentCreate(BaseModel):
    student_number: str
    full_name: str
    preferred_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    nationality: Optional[str] = None
    passport_number: Optional[str] = None
    visa_expiry: Optional[date] = None
    grade_level: Optional[str] = None
    class_name: Optional[str] = None
    homeroom_teacher_id: Optional[uuid.UUID] = None
    enrollment_date: Optional[date] = None
    notes: Optional[str] = None


class StudentUpdate(BaseModel):
    full_name: Optional[str] = None
    preferred_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    nationality: Optional[str] = None
    passport_number: Optional[str] = None
    visa_expiry: Optional[date] = None
    grade_level: Optional[str] = None
    class_name: Optional[str] = None
    homeroom_teacher_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    school_id: uuid.UUID
    student_number: str
    full_name: str
    preferred_name: Optional[str]
    date_of_birth: Optional[date]
    nationality: Optional[str]
    grade_level: Optional[str]
    class_name: Optional[str]
    photo_url: Optional[str]
    is_active: bool
    enrollment_date: Optional[date]
    created_at: datetime


class EmergencyContactCreate(BaseModel):
    name: str
    relationship_type: str
    phone_primary: str
    phone_secondary: Optional[str] = None
    email: Optional[EmailStr] = None
    priority: int = 1


class EmergencyContactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    relationship_type: str
    phone_primary: str
    phone_secondary: Optional[str]
    email: Optional[str]
    priority: int


class MedicalSummaryUpdate(BaseModel):
    allergies: Optional[str] = None
    medical_conditions: Optional[str] = None
    medications: Optional[str] = None
    doctor_name: Optional[str] = None
    doctor_phone: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_number: Optional[str] = None
    blood_type: Optional[str] = None
    additional_notes: Optional[str] = None


class MedicalSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    allergies: Optional[str]
    medical_conditions: Optional[str]
    medications: Optional[str]
    doctor_name: Optional[str]
    doctor_phone: Optional[str]
    blood_type: Optional[str]
    updated_at: datetime


# ── Attendance ────────────────────────────────────────────────────────────────
class AttendanceMarkItem(BaseModel):
    student_id: uuid.UUID
    status: AttendanceStatus
    check_in_time: Optional[datetime] = None
    notes: Optional[str] = None


class AttendanceBulkRequest(BaseModel):
    date: date
    records: List[AttendanceMarkItem]


class AttendanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    date: date
    status: AttendanceStatus
    check_in_time: Optional[datetime]
    is_excused: bool
    notes: Optional[str]
    created_at: datetime


class AbsenceExplanationCreate(BaseModel):
    attendance_id: uuid.UUID
    reason: str


class AbsenceExplanationReview(BaseModel):
    status: str  # approved/rejected
    review_notes: Optional[str] = None


class AttendanceStatsOut(BaseModel):
    date: date
    total_students: int
    present: int
    absent: int
    late: int
    excused: int
    attendance_rate: float


# ── Counseling ────────────────────────────────────────────────────────────────
class ReferralCreate(BaseModel):
    student_id: uuid.UUID
    reason: str
    urgency: str = "normal"


class ReferralUpdate(BaseModel):
    counselor_id: Optional[uuid.UUID] = None
    status: Optional[CaseStatus] = None
    closure_notes: Optional[str] = None


class ReferralOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    school_id: uuid.UUID
    student_id: uuid.UUID
    referred_by_id: uuid.UUID
    counselor_id: Optional[uuid.UUID]
    reason: str
    urgency: str
    status: CaseStatus
    created_at: datetime
    updated_at: datetime


class SessionCreate(BaseModel):
    referral_id: uuid.UUID
    session_date: datetime
    duration_minutes: int = 50
    notes: Optional[str] = None
    session_type: str = "individual"


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    referral_id: uuid.UUID
    counselor_id: uuid.UUID
    session_date: datetime
    duration_minutes: int
    session_type: str
    created_at: datetime


class FollowupCreate(BaseModel):
    referral_id: uuid.UUID
    assigned_to_id: uuid.UUID
    task: str
    due_date: datetime


class FollowupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    referral_id: uuid.UUID
    assigned_to_id: uuid.UUID
    task: str
    due_date: datetime
    is_completed: bool
    created_at: datetime


# ── Safeguarding ──────────────────────────────────────────────────────────────
class IncidentCreate(BaseModel):
    student_id: uuid.UUID
    risk_level: RiskLevel
    category: str
    description: str
    incident_date: date


class IncidentUpdate(BaseModel):
    risk_level: Optional[RiskLevel] = None
    status: Optional[IncidentStatus] = None
    assigned_to_id: Optional[uuid.UUID] = None


class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    school_id: uuid.UUID
    student_id: uuid.UUID
    reporter_id: uuid.UUID
    risk_level: RiskLevel
    category: str
    description: str
    incident_date: date
    status: IncidentStatus
    is_escalated: bool
    created_at: datetime
    updated_at: datetime


class IncidentNoteCreate(BaseModel):
    content: str


class EscalationCreate(BaseModel):
    escalated_to_id: uuid.UUID
    reason: str


# ── Notifications ─────────────────────────────────────────────────────────────
class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: str
    title: str
    body: str
    is_read: bool
    created_at: datetime


class NotificationPreferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: str
    email_enabled: bool
    push_enabled: bool
    in_app_enabled: bool


class PushTokenRegister(BaseModel):
    token: str
    platform: str = "web"


class BroadcastRequest(BaseModel):
    title: str
    body: str
    audience: str = "all"
    category: str = "announcement"


# ── Meetings ──────────────────────────────────────────────────────────────────
class MeetingBookRequest(BaseModel):
    teacher_id: uuid.UUID
    student_id: uuid.UUID
    scheduled_at: datetime
    duration_minutes: int = 15
    location: Optional[str] = None
    meeting_link: Optional[str] = None


class MeetingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    teacher_id: uuid.UUID
    parent_id: uuid.UUID
    student_id: uuid.UUID
    scheduled_at: datetime
    duration_minutes: int
    location: Optional[str]
    meeting_link: Optional[str]
    status: str
    created_at: datetime


# ── Announcements ─────────────────────────────────────────────────────────────
class AnnouncementCreate(BaseModel):
    title: str
    body: str
    audience: str = "all"
    expires_at: Optional[datetime] = None


class AnnouncementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    body: str
    audience: str
    is_published: bool
    published_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime


# ── Dashboard ─────────────────────────────────────────────────────────────────
class DashboardOverview(BaseModel):
    attendance_today_pct: float
    attendance_weekly_avg: float
    chronic_absentees: int
    open_counseling_cases: int
    open_safeguarding_incidents: int
    critical_incidents: int
    total_students: int
    at_risk_count: int


class AttendanceTrendPoint(BaseModel):
    date: date
    rate: float
    present: int
    absent: int


class AtRiskStudent(BaseModel):
    student_id: uuid.UUID
    full_name: str
    grade_level: Optional[str]
    class_name: Optional[str]
    consecutive_absences: int
    open_counseling: bool
    open_safeguarding: bool
