"""
tests/test_platform.py — Integration tests for International Student Care OS
Run: pytest tests/ -v --asyncio-mode=auto
"""

import pytest
import pytest_asyncio
import uuid
from datetime import date
from httpx import AsyncClient, ASGITransport

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

# ── In-memory SQLite engine for tests (no PostgreSQL required) ────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,       # single connection shared across the session
    echo=False,
)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ── Patch app to use test DB before importing app ─────────────────────────────
import api.core.database as _db_module
_db_module.engine = test_engine
_db_module.AsyncSessionLocal = TestSessionLocal

from appintersos import app                                     # noqa: E402
from api.core.database import Base                              # noqa: E402
from api.core.security import hash_password, create_access_token  # noqa: E402


# ── Session-scoped DB setup ───────────────────────────────────────────────────
@pytest_asyncio.fixture(scope="session")
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


# ── Per-test fixtures ─────────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def client(setup_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def school_and_admin(client: AsyncClient):
    """Create a school and admin user, return auth headers."""
    from api.models.core import School, User, SchoolUser, UserRole

    school_id = uuid.uuid4()
    user_id = uuid.uuid4()

    async with TestSessionLocal() as db:
        db.add(School(
            id=school_id,
            name="Test School",
            slug=f"test-school-{school_id.hex[:8]}",
            country="Thailand",
            timezone="Asia/Bangkok",
        ))
        db.add(User(
            id=user_id,
            email=f"admin-{user_id.hex[:8]}@test.edu",
            full_name="Test Admin",
            hashed_password=hash_password("password123"),
        ))
        db.add(SchoolUser(school_id=school_id, user_id=user_id, role=UserRole.SCHOOL_ADMIN))
        await db.commit()

    slug = f"test-school-{school_id.hex[:8]}"
    email = f"admin-{user_id.hex[:8]}@test.edu"
    token = create_access_token(str(user_id), str(school_id), "school_admin")
    headers = {"Authorization": f"Bearer {token}"}
    return {
        "school_id": str(school_id),
        "user_id": str(user_id),
        "headers": headers,
        "slug": slug,
        "email": email,
    }


@pytest_asyncio.fixture
async def student(school_and_admin, client: AsyncClient):
    resp = await client.post("/api/v1/students", json={
        "student_number": f"S{uuid.uuid4().hex[:6]}",
        "full_name": "Alice Smith",
        "grade_level": "G10",
        "class_name": "10A",
        "nationality": "British",
    }, headers=school_and_admin["headers"])
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── Health check ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"


# ── Auth ──────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_login_success(school_and_admin, client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={
        "email": school_and_admin["email"],
        "password": "password123",
        "school_slug": school_and_admin["slug"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == school_and_admin["email"]


@pytest.mark.asyncio
async def test_login_wrong_password(school_and_admin, client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={
        "email": school_and_admin["email"],
        "password": "wrongpassword",
        "school_slug": school_and_admin["slug"],
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_school(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "admin@test.edu",
        "password": "password123",
        "school_slug": "nonexistent-school",
    })
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_me_endpoint(school_and_admin, client: AsyncClient):
    resp = await client.get("/api/v1/auth/me", headers=school_and_admin["headers"])
    assert resp.status_code == 200
    assert resp.json()["email"] == school_and_admin["email"]


@pytest.mark.asyncio
async def test_me_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code in (401, 403)


# ── Students ──────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_create_student(school_and_admin, client: AsyncClient):
    resp = await client.post("/api/v1/students", json={
        "student_number": f"S{uuid.uuid4().hex[:6]}",
        "full_name": "Bob Jones",
        "grade_level": "G11",
        "class_name": "11B",
    }, headers=school_and_admin["headers"])
    assert resp.status_code == 201
    data = resp.json()
    assert data["full_name"] == "Bob Jones"
    assert data["grade_level"] == "G11"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_list_students(school_and_admin, student, client: AsyncClient):
    resp = await client.get("/api/v1/students", headers=school_and_admin["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_search_students(school_and_admin, student, client: AsyncClient):
    resp = await client.get("/api/v1/students?q=Alice", headers=school_and_admin["headers"])
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert any(s["full_name"] == "Alice Smith" for s in items)


@pytest.mark.asyncio
async def test_get_student(school_and_admin, student, client: AsyncClient):
    resp = await client.get(f"/api/v1/students/{student['id']}", headers=school_and_admin["headers"])
    assert resp.status_code == 200
    assert resp.json()["id"] == student["id"]


@pytest.mark.asyncio
async def test_update_student(school_and_admin, student, client: AsyncClient):
    resp = await client.put(
        f"/api/v1/students/{student['id']}",
        json={"class_name": "10B"},
        headers=school_and_admin["headers"],
    )
    assert resp.status_code == 200
    assert resp.json()["class_name"] == "10B"


@pytest.mark.asyncio
async def test_deactivate_student(school_and_admin, student, client: AsyncClient):
    resp = await client.delete(f"/api/v1/students/{student['id']}", headers=school_and_admin["headers"])
    assert resp.status_code == 200
    get_resp = await client.get(f"/api/v1/students/{student['id']}", headers=school_and_admin["headers"])
    assert get_resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_emergency_contact(school_and_admin, student, client: AsyncClient):
    resp = await client.post(
        f"/api/v1/students/{student['id']}/emergency-contacts",
        json={
            "name": "Jane Smith",
            "relationship_type": "Mother",   # fixed: was "relationship"
            "phone_primary": "+44 7700 900000",
            "priority": 1,
        },
        headers=school_and_admin["headers"],
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Jane Smith"


# ── Attendance ────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_bulk_mark_attendance(school_and_admin, student, client: AsyncClient):
    today = date.today().isoformat()
    resp = await client.post("/api/v1/attendance/bulk", json={
        "date": today,
        "records": [{"student_id": student["id"], "status": "present"}],
    }, headers=school_and_admin["headers"])
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_get_attendance_stats(school_and_admin, student, client: AsyncClient):
    today = date.today().isoformat()
    resp = await client.get(f"/api/v1/attendance/stats?date={today}", headers=school_and_admin["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert "attendance_rate" in data
    assert "total_students" in data


@pytest.mark.asyncio
async def test_student_attendance_history(school_and_admin, student, client: AsyncClient):
    resp = await client.get(f"/api/v1/attendance/student/{student['id']}", headers=school_and_admin["headers"])
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── Counseling ────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_create_referral(school_and_admin, student, client: AsyncClient):
    resp = await client.post("/api/v1/counseling/referrals", json={
        "student_id": student["id"],
        "reason": "Student appears withdrawn and has missed several deadlines.",
        "urgency": "high",
    }, headers=school_and_admin["headers"])
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "open"
    assert data["urgency"] == "high"


@pytest.mark.asyncio
async def test_list_referrals(school_and_admin, client: AsyncClient):
    resp = await client.get("/api/v1/counseling/referrals", headers=school_and_admin["headers"])
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── Safeguarding ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_report_incident(school_and_admin, student, client: AsyncClient):
    resp = await client.post("/api/v1/safeguarding/incidents", json={
        "student_id": student["id"],
        "risk_level": "medium",
        "category": "Bullying",
        "description": "Student reported being bullied by classmates during lunch break.",
        "incident_date": date.today().isoformat(),
    }, headers=school_and_admin["headers"])
    assert resp.status_code == 201
    data = resp.json()
    assert data["risk_level"] == "medium"
    assert data["status"] == "open"


@pytest.mark.asyncio
async def test_list_incidents(school_and_admin, client: AsyncClient):
    resp = await client.get("/api/v1/safeguarding/incidents", headers=school_and_admin["headers"])
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_add_incident_note(school_and_admin, student, client: AsyncClient):
    inc_resp = await client.post("/api/v1/safeguarding/incidents", json={
        "student_id": student["id"],
        "risk_level": "low",
        "category": "Other",
        "description": "Test incident for note testing.",
        "incident_date": date.today().isoformat(),
    }, headers=school_and_admin["headers"])
    inc_id = inc_resp.json()["id"]
    resp = await client.post(f"/api/v1/safeguarding/incidents/{inc_id}/notes", json={
        "content": "Follow-up completed. Student spoke with counselor.",
    }, headers=school_and_admin["headers"])
    assert resp.status_code == 200


# ── Dashboard ─────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_dashboard_overview(school_and_admin, client: AsyncClient):
    resp = await client.get("/api/v1/dashboard/overview", headers=school_and_admin["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert "attendance_today_pct" in data
    assert "total_students" in data
    assert "open_counseling_cases" in data
    assert "open_safeguarding_incidents" in data


@pytest.mark.asyncio
async def test_attendance_trend(school_and_admin, client: AsyncClient):
    resp = await client.get("/api/v1/dashboard/attendance-trend?days=7", headers=school_and_admin["headers"])
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_at_risk_students(school_and_admin, client: AsyncClient):
    resp = await client.get("/api/v1/dashboard/at-risk-students", headers=school_and_admin["headers"])
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── Notifications ─────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_get_notifications(school_and_admin, client: AsyncClient):
    resp = await client.get("/api/v1/notifications", headers=school_and_admin["headers"])
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── RBAC ──────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_rbac_student_cannot_report_incident(school_and_admin, student, client: AsyncClient):
    from api.models.core import UserRole
    student_token = create_access_token(
        str(uuid.uuid4()), school_and_admin["school_id"], UserRole.STUDENT.value
    )
    resp = await client.post("/api/v1/safeguarding/incidents", json={
        "student_id": student["id"],
        "risk_level": "low",
        "category": "Other",
        "description": "Should not be allowed.",
        "incident_date": date.today().isoformat(),
    }, headers={"Authorization": f"Bearer {student_token}"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_rbac_parent_cannot_access_counseling(school_and_admin, client: AsyncClient):
    parent_token = create_access_token(str(uuid.uuid4()), school_and_admin["school_id"], "parent")
    resp = await client.get("/api/v1/counseling/referrals", headers={"Authorization": f"Bearer {parent_token}"})
    assert resp.status_code == 403
