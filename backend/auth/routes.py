"""
Auth endpoints.

/auth/login is a STUB for Milestone 1: it validates the request shape and
issues a real JWT, but does not check credentials against a real user store
yet. That lands with proper user management in a later milestone.
"""
from fastapi import APIRouter, Depends, Request, HTTPException, status
from pydantic import BaseModel, Field
import bcrypt

from auth.jwt_handler import create_access_token, get_current_subject
from core.config import settings
from core.rate_limit import limiter
from models.response import APIResponse

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=256)


class LoginResponseData(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=APIResponse[LoginResponseData])
@limiter.limit("10/minute")
async def login(request: Request, payload: LoginRequest):
    if not settings.demo_password_hash:
        # No credential configured (e.g. local dev with .env.example defaults) —
        # keep the original M1 stub behavior so local development still works
        # without extra setup.
        token = create_access_token(subject=payload.username)
        return APIResponse(success=True, data=LoginResponseData(access_token=token))

    # Real check against the single configured demo credential. Always run
    # both comparisons (never short-circuit on username) and return an
    # identical generic error either way, so failed attempts can't be used
    # to enumerate the valid username.
    username_ok = payload.username == settings.demo_username
    try:
        password_ok = bcrypt.checkpw(
            payload.password.encode("utf-8")[:72],  # bcrypt's own 72-byte input limit
            settings.demo_password_hash.encode("utf-8"),
        )
    except ValueError:
        # Malformed hash in config — fail closed, never treat as a match.
        password_ok = False

    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = create_access_token(subject=payload.username)
    return APIResponse(success=True, data=LoginResponseData(access_token=token))


@router.get("/me", response_model=APIResponse[dict])
async def whoami(subject: str = Depends(get_current_subject)):
    """Protected route used to verify the JWT round-trip works end-to-end."""
    return APIResponse(success=True, data={"subject": subject})
