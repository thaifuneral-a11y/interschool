"""api/models/core.py — Core ORM models"""

import uuid
import enum
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import (
    String, Enum, ForeignKey, Text, Boolean, DateTime,
    Date, Integer, JSON, UniqueConstraint, Index, TypeDecorator, CHAR
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid as _uuid_mod


class UUID(TypeDecorator):
    """Platform-independent UUID type.
    Uses PostgreSQL native UUID on Postgres, plain String(36) on SQLite.
    Transparently converts str <-> uuid.UUID so all dialects work identically.
    """
    impl = String
    cache_ok = True

    def __init__(self, as_uuid: bool = True):
        self.as_uuid = as_uuid
        super().__init__(36)

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=self.as_uuid))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        """Convert any UUID representation to the form the DB expects."""
        if value is None:
            return None
        if isinstance(value, _uuid_mod.UUID):
            if dialect.name == "postgresql":
                return value
            return str(value)
        # It's a string — convert to uuid.UUID first to validate, then back
        try:
            parsed = _uuid_mod.UUID(str(value))
        except (ValueError, AttributeError):
            return str(value)
        if dialect.name == "postgresql":
            return parsed
        return str(parsed)

    def process_result_value(self, value, dialect):
        """Convert DB value back to uuid.UUID (or str if as_uuid=False)."""
        if value is None:
            return None
        if not self.as_uuid:
            return str(value)
        if isinstance(value, _uuid_mod.UUID):
            return value
        try:
            return _uuid_mod.UUID(str(value))
        except (ValueError, AttributeError):
            return value

from api.core.database import Base


# ── Enums ─────────────────────────────────────────────────────────────────────
class UserRole(str, enum.Enum):
    SUPER_ADMIN  = "super_admin"
    SCHOOL_ADMIN = "school_admin"
    PRINCIPAL    = "principal"
    TEACHER      = "teacher"
    COUNSELOR    = "counselor"
    PARENT       = "parent"
    STUDENT      = "student"


class AttendanceStatus(str, enum.Enum):
    PRESENT  = "present"
    ABSENT   = "absent"
    LATE     = "late"
    EXCUSED  = "excused"
    HALF_DAY = "half_day"


class RiskLevel(str, enum.Enum):
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


class CaseStatus(str, enum.Enum):
    OPEN     = "open"
    ACTIVE   = "active"
    CLOSED   = "closed"
    ARCHIVED = "archived"


class IncidentStatus(str, enum.Enum):
    OPEN       = "open"
    UNDER_REVIEW = "under_review"
    ESCALATED  = "escalated"
    RESOLVED   = "resolved"


class NotificationChannel(str, enum.Enum):
    EMAIL = "email"
    PUSH  = "push"
    IN_APP = "in_app"


# ── Schools ───────────────────────────────────────────────────────────────────
class School(Base):
    __tablename__ = "schools"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    country: Mapped[str] = mapped_column(String(100))
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    logo_url: Mapped[Optional[str]] = mapped_column(String(500))
    address: Mapped[Optional[str]] = mapped_column(Text)
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    website: Mapped[Optional[str]] = mapped_column(String(255))
    academic_year_start: Mapped[Optional[int]] = mapped_column(Integer)  # month
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    settings: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    users: Mapped[List["SchoolUser"]] = relationship("SchoolUser", back_populates="school")
    students: Mapped[List["Student"]] = relationship("Student", back_populates="school")


# ── Users ─────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))
    google_sub: Mapped[Optional[str]] = mapped_column(String(255), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_super_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    school_memberships: Mapped[List["SchoolUser"]] = relationship("SchoolUser", back_populates="user")
    push_tokens: Mapped[List["PushToken"]] = relationship("PushToken", back_populates="user")


class SchoolUser(Base):
    """Many-to-many: User ↔ School with role."""
    __tablename__ = "school_users"
    __table_args__ = (UniqueConstraint("school_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schools.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    school: Mapped["School"] = relationship("School", back_populates="users")
    user: Mapped["User"] = relationship("User", back_populates="school_memberships")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


# ── Students ──────────────────────────────────────────────────────────────────
class Student(Base):
    __tablename__ = "students"
    __table_args__ = (Index("ix_students_school_grade", "school_id", "grade_level"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schools.id", ondelete="CASCADE"))
    student_number: Mapped[str] = mapped_column(String(50))
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    preferred_name: Mapped[Optional[str]] = mapped_column(String(100))
    date_of_birth: Mapped[Optional[datetime]] = mapped_column(Date)
    nationality: Mapped[Optional[str]] = mapped_column(String(100))
    passport_number: Mapped[Optional[str]] = mapped_column(String(50))
    visa_expiry: Mapped[Optional[datetime]] = mapped_column(Date)
    grade_level: Mapped[Optional[str]] = mapped_column(String(20))
    class_name: Mapped[Optional[str]] = mapped_column(String(50))
    homeroom_teacher_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    photo_url: Mapped[Optional[str]] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    enrollment_date: Mapped[Optional[datetime]] = mapped_column(Date)
    departure_date: Mapped[Optional[datetime]] = mapped_column(Date)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    school: Mapped["School"] = relationship("School", back_populates="students")
    emergency_contacts: Mapped[List["EmergencyContact"]] = relationship("EmergencyContact", back_populates="student")
    medical_summary: Mapped[Optional["MedicalSummary"]] = relationship("MedicalSummary", back_populates="student", uselist=False)
    parent_links: Mapped[List["StudentParent"]] = relationship("StudentParent", back_populates="student")
    attendance_records: Mapped[List["AttendanceRecord"]] = relationship("AttendanceRecord", back_populates="student")


class EmergencyContact(Base):
    __tablename__ = "emergency_contacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(100))
    phone_primary: Mapped[str] = mapped_column(String(50))
    phone_secondary: Mapped[Optional[str]] = mapped_column(String(50))
    email: Mapped[Optional[str]] = mapped_column(String(320))
    priority: Mapped[int] = mapped_column(Integer, default=1)

    student: Mapped["Student"] = relationship("Student", back_populates="emergency_contacts")


class MedicalSummary(Base):
    __tablename__ = "medical_summaries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), unique=True)
    allergies: Mapped[Optional[str]] = mapped_column(Text)
    medical_conditions: Mapped[Optional[str]] = mapped_column(Text)
    medications: Mapped[Optional[str]] = mapped_column(Text)
    doctor_name: Mapped[Optional[str]] = mapped_column(String(255))
    doctor_phone: Mapped[Optional[str]] = mapped_column(String(50))
    insurance_provider: Mapped[Optional[str]] = mapped_column(String(255))
    insurance_number: Mapped[Optional[str]] = mapped_column(String(100))
    blood_type: Mapped[Optional[str]] = mapped_column(String(10))
    additional_notes: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    student: Mapped["Student"] = relationship("Student", back_populates="medical_summary")


class StudentParent(Base):
    __tablename__ = "student_parents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    relationship_type: Mapped[str] = mapped_column(String(50), default="parent")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    can_pickup: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    student: Mapped["Student"] = relationship("Student", back_populates="parent_links")
    user: Mapped["User"] = relationship("User")


# ── Attendance ────────────────────────────────────────────────────────────────
class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint("student_id", "date"),
        Index("ix_attendance_school_date", "school_id", "date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schools.id", ondelete="CASCADE"))
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    status: Mapped[AttendanceStatus] = mapped_column(Enum(AttendanceStatus), nullable=False)
    check_in_time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    marked_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_excused: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    student: Mapped["Student"] = relationship("Student", back_populates="attendance_records")


class AbsenceExplanation(Base):
    __tablename__ = "absence_explanations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attendance_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("attendance_records.id", ondelete="CASCADE"))
    submitted_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_url: Mapped[Optional[str]] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/approved/rejected
    reviewed_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    review_notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)


# ── Counseling ────────────────────────────────────────────────────────────────
class CounselingReferral(Base):
    __tablename__ = "counseling_referrals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schools.id", ondelete="CASCADE"))
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"))
    referred_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    counselor_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    urgency: Mapped[str] = mapped_column(String(20), default="normal")  # low/normal/high/urgent
    status: Mapped[CaseStatus] = mapped_column(Enum(CaseStatus), default=CaseStatus.OPEN)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    closure_notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    sessions: Mapped[List["CounselingSession"]] = relationship("CounselingSession", back_populates="referral")
    followups: Mapped[List["CounselingFollowup"]] = relationship("CounselingFollowup", back_populates="referral")


class CounselingSession(Base):
    __tablename__ = "counseling_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    referral_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("counseling_referrals.id", ondelete="CASCADE"))
    counselor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    session_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=50)
    notes: Mapped[Optional[str]] = mapped_column(Text)  # Confidential
    session_type: Mapped[str] = mapped_column(String(50), default="individual")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    referral: Mapped["CounselingReferral"] = relationship("CounselingReferral", back_populates="sessions")


class CounselingFollowup(Base):
    __tablename__ = "counseling_followups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    referral_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("counseling_referrals.id", ondelete="CASCADE"))
    assigned_to_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    task: Mapped[str] = mapped_column(Text, nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    referral: Mapped["CounselingReferral"] = relationship("CounselingReferral", back_populates="followups")


# ── Safeguarding ──────────────────────────────────────────────────────────────
class SafeguardingIncident(Base):
    __tablename__ = "safeguarding_incidents"
    __table_args__ = (Index("ix_safeguarding_school_risk", "school_id", "risk_level"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schools.id", ondelete="CASCADE"))
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"))
    reporter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    assigned_to_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    risk_level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel), nullable=False)
    category: Mapped[str] = mapped_column(String(100))  # abuse, neglect, bullying, self-harm etc.
    description: Mapped[str] = mapped_column(Text, nullable=False)
    incident_date: Mapped[datetime] = mapped_column(Date)
    status: Mapped[IncidentStatus] = mapped_column(Enum(IncidentStatus), default=IncidentStatus.OPEN)
    is_escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    escalated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    notes: Mapped[List["IncidentNote"]] = relationship("IncidentNote", back_populates="incident")
    escalations: Mapped[List["SafeguardingEscalation"]] = relationship("SafeguardingEscalation", back_populates="incident")


class IncidentNote(Base):
    __tablename__ = "incident_notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("safeguarding_incidents.id", ondelete="CASCADE"))
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    incident: Mapped["SafeguardingIncident"] = relationship("SafeguardingIncident", back_populates="notes")


class SafeguardingEscalation(Base):
    __tablename__ = "safeguarding_escalations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("safeguarding_incidents.id", ondelete="CASCADE"))
    escalated_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    escalated_to_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(Text)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    incident: Mapped["SafeguardingIncident"] = relationship("SafeguardingIncident", back_populates="escalations")


# ── Notifications ─────────────────────────────────────────────────────────────
class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("schools.id"))
    recipient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    channel: Mapped[NotificationChannel] = mapped_column(Enum(NotificationChannel))
    category: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class PushToken(Base):
    __tablename__ = "push_tokens"
    __table_args__ = (UniqueConstraint("user_id", "token"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token: Mapped[str] = mapped_column(String(500), nullable=False)
    platform: Mapped[str] = mapped_column(String(20), default="web")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    user: Mapped["User"] = relationship("User", back_populates="push_tokens")


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (UniqueConstraint("user_id", "category"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    category: Mapped[str] = mapped_column(String(50))
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True)


# ── Meetings ──────────────────────────────────────────────────────────────────
class ParentTeacherMeeting(Base):
    __tablename__ = "parent_teacher_meetings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schools.id", ondelete="CASCADE"))
    teacher_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    parent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id"))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=15)
    location: Mapped[Optional[str]] = mapped_column(String(255))
    meeting_link: Mapped[Optional[str]] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="confirmed")  # confirmed/cancelled
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


# ── Announcements ─────────────────────────────────────────────────────────────
class SchoolAnnouncement(Base):
    __tablename__ = "school_announcements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schools.id", ondelete="CASCADE"))
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    audience: Mapped[str] = mapped_column(String(50), default="all")  # all/parents/staff
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


# ── Audit Log ─────────────────────────────────────────────────────────────────
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("schools.id"))
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100))
    resource_id: Mapped[Optional[str]] = mapped_column(String(255))
    old_value: Mapped[Optional[dict]] = mapped_column(JSON)
    new_value: Mapped[Optional[dict]] = mapped_column(JSON)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), index=True)
