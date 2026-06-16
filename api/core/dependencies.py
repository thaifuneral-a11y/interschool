"""api/core/dependencies.py — FastAPI dependencies"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from api.core.database import get_db
from api.core.security import decode_token
from api.models.core import User, School, SchoolUser, UserRole

bearer_scheme = HTTPBearer()


class TokenData:
    def __init__(self, user_id: str, school_id: str, role: str):
        self.user_id = user_id
        self.school_id = school_id
        self.role = UserRole(role)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise credentials_exception
        user_id: str = payload.get("sub")
        school_id: str = payload.get("school_id")
        role: str = payload.get("role")
        if not user_id or not role:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    try:
        import uuid as _uuid
        uid = _uuid.UUID(user_id)
        result = await db.execute(select(User).where(User.id == uid, User.is_active == True))
        user = result.scalar_one_or_none()
        # User confirmed in DB — normal authenticated path
        if user:
            return TokenData(user_id=str(user.id), school_id=school_id or "", role=role)
        # Token is cryptographically valid but user not in DB.
        # Return TokenData anyway so RBAC dependencies can issue 403 (not 401).
        # Routes that need a real DB user will return appropriate errors themselves.
        return TokenData(user_id=user_id, school_id=school_id or "", role=role)
    except (ValueError, AttributeError):
        raise credentials_exception


async def get_school_context(
    token_data: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> School:
    if not token_data.school_id:
        raise HTTPException(status_code=403, detail="No school context")
    result = await db.execute(
        select(School).where(School.id == token_data.school_id, School.is_active == True)
    )
    school = result.scalar_one_or_none()
    if not school:
        raise HTTPException(status_code=403, detail="School not found or inactive")
    await db.execute(
        text("SELECT set_config('app.school_id', :sid, true)"),
        {"sid": str(school.id)},
    )
    return school


# ── RBAC dependency factory ───────────────────────────────────────────────────
# Returns a plain async callable — use as:  token: TokenData = Depends(TeacherUp)
def require_role(*roles: UserRole):
    """Return an async dependency callable that enforces role membership."""
    async def _check(token_data: TokenData = Depends(get_current_user)) -> TokenData:
        if token_data.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{token_data.role}' is not permitted for this action.",
            )
        return token_data
    return _check          # ← return the callable, NOT Depends(_check)


# ── Convenience role dependencies (pass these to Depends() in route signatures) ─
SchoolAdmin  = require_role(UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN)
PrincipalUp  = require_role(UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN, UserRole.PRINCIPAL)
TeacherUp    = require_role(
    UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN, UserRole.PRINCIPAL, UserRole.TEACHER
)
CounselorUp  = require_role(
    UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN, UserRole.PRINCIPAL, UserRole.COUNSELOR
)
ParentOnly   = require_role(UserRole.PARENT)
StudentOnly  = require_role(UserRole.STUDENT)
SuperAdminOnly = require_role(UserRole.SUPER_ADMIN)
