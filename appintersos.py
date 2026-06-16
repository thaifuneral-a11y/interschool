"""
appintersos.py — International Student Care OS
Entry point: uvicorn appintersos:app --reload --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from api.core.config import settings
from api.core.database import engine, Base
from api.core.logging import setup_logging
from api.routers import (
    auth,
    students,
    attendance,
    parents,
    counseling,
    safeguarding,
    notifications,
    dashboard,
    admin,
)

setup_logging()
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title="International Student Care OS",
    description="Student wellbeing and support platform for international schools.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
    contact={"name": "Platform Support", "email": "support@intersos.edu"},
    license_info={"name": "Proprietary"},
)

# ── Middleware ────────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.ENVIRONMENT == "production":
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)


# ── Security headers (pure ASGI — avoids BaseHTTPMiddleware task-leak in tests) ──
class SecurityHeadersMiddleware:
    """Adds security headers without using BaseHTTPMiddleware."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                headers[b"x-content-type-options"] = b"nosniff"
                headers[b"x-frame-options"] = b"DENY"
                headers[b"x-xss-protection"] = b"1; mode=block"
                headers[b"referrer-policy"] = b"strict-origin-when-cross-origin"
                if settings.ENVIRONMENT == "production":
                    headers[b"strict-transport-security"] = b"max-age=63072000; includeSubDomains"
                message = {**message, "headers": list(headers.items())}
            await send(message)

        await self.app(scope, receive, send_with_headers)

app.add_middleware(SecurityHeadersMiddleware)


# ── Routers ───────────────────────────────────────────────────────────────────
PREFIX = "/api/v1"
app.include_router(auth.router,          prefix=PREFIX, tags=["Authentication"])
app.include_router(students.router,      prefix=PREFIX, tags=["Students"])
app.include_router(attendance.router,    prefix=PREFIX, tags=["Attendance"])
app.include_router(parents.router,       prefix=PREFIX, tags=["Parent Portal"])
app.include_router(counseling.router,    prefix=PREFIX, tags=["Counseling"])
app.include_router(safeguarding.router,  prefix=PREFIX, tags=["Safeguarding"])
app.include_router(notifications.router, prefix=PREFIX, tags=["Notifications"])
app.include_router(dashboard.router,     prefix=PREFIX, tags=["Dashboard"])
app.include_router(admin.router,         prefix=PREFIX, tags=["Admin"])


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "version": "1.0.0", "app": "International Student Care OS"}


# ── Global error handler ──────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc) if settings.DEBUG else None},
    )
