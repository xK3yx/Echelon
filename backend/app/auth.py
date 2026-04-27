"""
Admin token authentication dependency.

Usage:
    @router.post("/admin/careers", dependencies=[Depends(require_admin)])
    async def create_career(...): ...

The token is a single shared secret read from the ADMIN_TOKEN env var.
An empty or unset ADMIN_TOKEN disables all admin endpoints (returns 503).
This is intentionally minimal — not a multi-user auth system.
"""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

_bearer = HTTPBearer(auto_error=False)


async def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> None:
    if not settings.admin_token:
        raise HTTPException(
            status_code=503,
            detail="Admin features are disabled (ADMIN_TOKEN is not configured).",
        )
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authorization header with Bearer token required.",
        )
    if credentials.credentials != settings.admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token.")
