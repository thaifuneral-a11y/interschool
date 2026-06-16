"""api/routers/auth.py — Authentication endpoints"""

import hashlib
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.core.database import get_db
from api.core.security import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    decode_token, create_invite_token, create_password_reset_token, verify_google_token
)
from api.core.dependencies import get_current_user, TokenData
from api.models.core import User, School, SchoolUser, RefreshToken, UserRole
from api.schemas.all import (
    LoginRequest, GoogleAuthRequest, TokenResponse, RefreshRequest,
    ForgotPasswordRequest, ResetPasswordRequest, InviteUserRequest,
    AcceptInviteRequest, UserOut, SuccessResponse
)
from api.services.email import send_password_reset_email, send_invite_email
from api.services.audit import log_action

router = APIRouter(prefix="/auth")


async def _get_school_by_slug(db: AsyncSession, slug: str) -> School:
    result = await db.execute(select(School).where(School.slug == slug, School.is_active == True))
    school = result.scalar_one_or_none()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    return school


async def _get_school_user(db: AsyncSession, user_id, school_id) -> SchoolUser:
    result = await db.execute(
        select(SchoolUser).where(
            SchoolUser.user_id == user_id,
            SchoolUser.school_id == school_id,
            SchoolUser.is_active == True,
        )
    )
    return result.scalar_one_or_none()


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    school = await _get_school_by_slug(db, body.school_slug)

    result = await db.execute(select(User).where(User.email == body.email, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user or not user.hashed_password or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    su = await _get_school_user(db, user.id, school.id)
    if not su and not user.is_super_admin:
        raise HTTPException(status_code=403, detail="User not registered with this school")

    role = UserRole.SUPER_ADMIN if user.is_super_admin else su.role
    access_token = create_access_token(str(user.id), str(school.id), role.value)
    refresh_token = create_refresh_token(str(user.id))

    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    from datetime import timedelta
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7),
    ))
    user.last_login_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()

    background_tasks.add_task(
        log_action, db, str(user.id), str(school.id), "login", "user", str(user.id),
        ip=request.client.host if request.client else None
    )

    return TokenResponse(
        access_token=access_token,
        expires_in=1800,
        user=UserOut.model_validate(user),
    )


@router.post("/google", response_model=TokenResponse)
async def google_auth(body: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    idinfo = verify_google_token(body.id_token)
    if not idinfo:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    school = await _get_school_by_slug(db, body.school_slug)
    email = idinfo["email"]
    google_sub = idinfo["sub"]

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            email=email,
            full_name=idinfo.get("name", email),
            google_sub=google_sub,
            avatar_url=idinfo.get("picture"),
        )
        db.add(user)
        await db.flush()

    if not user.google_sub:
        user.google_sub = google_sub

    su = await _get_school_user(db, user.id, school.id)
    if not su and not user.is_super_admin:
        raise HTTPException(status_code=403, detail="Not registered with this school")

    role = UserRole.SUPER_ADMIN if user.is_super_admin else su.role
    access_token = create_access_token(str(user.id), str(school.id), role.value)
    refresh_token = create_refresh_token(str(user.id))

    await db.commit()
    return TokenResponse(
        access_token=access_token,
        expires_in=1800,
        user=UserOut.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload["sub"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    token_hash = hashlib.sha256(body.refresh_token.encode()).hexdigest()
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked == False,
        )
    )
    stored = result.scalar_one_or_none()
    if not stored or stored.expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(status_code=401, detail="Refresh token expired or revoked")

    stored.revoked = True

    result2 = await db.execute(select(User).where(User.id == user_id))
    user = result2.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Use first active school membership
    result3 = await db.execute(
        select(SchoolUser).where(SchoolUser.user_id == user.id, SchoolUser.is_active == True).limit(1)
    )
    su = result3.scalar_one_or_none()
    school_id = str(su.school_id) if su else ""
    role = UserRole.SUPER_ADMIN if user.is_super_admin else (su.role if su else UserRole.STUDENT)

    new_access = create_access_token(str(user.id), school_id, role.value)
    new_refresh = create_refresh_token(str(user.id))
    new_hash = hashlib.sha256(new_refresh.encode()).hexdigest()
    from datetime import timedelta
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=new_hash,
        expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7),
    ))
    await db.commit()

    return TokenResponse(access_token=new_access, expires_in=1800, user=UserOut.model_validate(user))


@router.post("/logout", response_model=SuccessResponse)
async def logout(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    token_hash = hashlib.sha256(body.refresh_token.encode()).hexdigest()
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    stored = result.scalar_one_or_none()
    if stored:
        stored.revoked = True
        await db.commit()
    return SuccessResponse(message="Logged out successfully")


@router.post("/forgot-password", response_model=SuccessResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user:
        token = create_password_reset_token(str(user.id))
        background_tasks.add_task(send_password_reset_email, user.email, user.full_name, token)
    return SuccessResponse(message="If this email exists, a reset link has been sent.")


@router.post("/reset-password", response_model=SuccessResponse)
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(body.token)
        if payload.get("type") != "password_reset":
            raise ValueError
        user_id = payload["sub"]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = hash_password(body.new_password)
    await db.commit()
    return SuccessResponse(message="Password updated successfully")


@router.post("/invite", response_model=SuccessResponse)
async def invite_user(
    body: InviteUserRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    token_data: TokenData = Depends(get_current_user),
):
    if token_data.role not in (UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN, UserRole.PRINCIPAL):
        raise HTTPException(status_code=403, detail="Not permitted")

    token = create_invite_token(body.email, token_data.school_id, body.role.value)
    background_tasks.add_task(
        send_invite_email, body.email, body.full_name, token_data.school_id, token
    )
    return SuccessResponse(message=f"Invitation sent to {body.email}")


@router.post("/accept-invite", response_model=TokenResponse)
async def accept_invite(body: AcceptInviteRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(body.token)
        if payload.get("type") != "invite":
            raise ValueError
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired invite token")

    email = payload["email"]
    school_id = payload["school_id"]
    role = payload["role"]

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        user = User(email=email, full_name=email.split("@")[0], hashed_password=hash_password(body.password))
        db.add(user)
        await db.flush()
    else:
        user.hashed_password = hash_password(body.password)

    existing_su = await _get_school_user(db, user.id, school_id)
    if not existing_su:
        db.add(SchoolUser(school_id=school_id, user_id=user.id, role=UserRole(role)))

    await db.commit()
    access_token = create_access_token(str(user.id), school_id, role)
    return TokenResponse(access_token=access_token, expires_in=1800, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def me(
    token_data: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == token_data.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut.model_validate(user)
