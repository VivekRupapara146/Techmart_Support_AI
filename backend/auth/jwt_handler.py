"""
JWT creation/validation utilities.

NOTE: The /auth/login endpoint in routes.py is a STUB for this milestone —
it issues valid tokens but does not yet verify against a real user store.
Do not treat it as production-ready auth. Real user verification arrives
in a later milestone.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from core.config import settings

# auto_error=False lets us raise our own 401 (instead of FastAPI's default 403)
# when no Authorization header is present, so missing-token and invalid-token
# cases behave consistently.
bearer_scheme = HTTPBearer(auto_error=False)


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
        )


def get_current_subject(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> str:
    """Dependency for protected routes — resolves the JWT subject (session/user id)."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    payload = decode_access_token(credentials.credentials)
    subject = payload.get("sub")
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim",
        )
    return subject
