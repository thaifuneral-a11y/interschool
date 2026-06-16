"""api/core/security.py — JWT, bcrypt, Google OAuth"""

import uuid
import bcrypt
from datetime import datetime, timezone, timedelta
from typing import Optional

from jose import JWTError, jwt
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

from api.core.config import settings


# ── Password (using bcrypt directly — passlib has a compatibility bug with
#    newer bcrypt versions that causes ValueError during backend init) ──────────
def hash_password(password: str) -> str:
    """Hash a password using bcrypt. Encodes to bytes and truncates at 72."""
    pwd_bytes = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    pwd_bytes = plain.encode("utf-8")[:72]
    try:
        return bcrypt.checkpw(pwd_bytes, hashed.encode("utf-8"))
    except Exception:
        return False


# ── JWT ───────────────────────────────────────────────────────────────────────
def create_access_token(user_id: str, school_id: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "school_id": school_id,
        "role": role,
        "exp": datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc).replace(tzinfo=None),
        "type": "access",
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": datetime.now(timezone.utc).replace(tzinfo=None),
        "type": "refresh",
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def create_invite_token(email: str, school_id: str, role: str) -> str:
    payload = {
        "email": email,
        "school_id": school_id,
        "role": role,
        "exp": datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7),
        "type": "invite",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_password_reset_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=2),
        "type": "password_reset",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# ── Google OAuth ──────────────────────────────────────────────────────────────
def verify_google_token(token: str) -> Optional[dict]:
    try:
        idinfo = google_id_token.verify_oauth2_token(
            token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
        return idinfo
    except ValueError:
        return None
