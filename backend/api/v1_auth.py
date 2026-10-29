"""
Versioned login endpoint — the contract the React frontend speaks
(frontend/src/services/apiClient.ts: login()). Same single-demo-account
check as the legacy /auth/login (auth/service.py), reshaped into the
richer response the frontend expects: a `user` object and `expires_in`.

Still not a real multi-user system — see auth/service.py's docstring and
core/security_startup.py for the production guard that requires a real
DEMO_PASSWORD_HASH before the app will even start in production.
"""
from fastapi import APIRouter, Request, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel

from auth.jwt_handler import create_access_token
from auth.service import authenticate_demo_account
from core.config import settings
from core.rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["auth (v1)"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=256)


class LoginUser(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    name: str
    email: str
    role: str
    initials: str


class LoginResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    access_token: str
    token_type: str = "bearer"
    user: LoginUser
    expires_in: int


def _derive_user(username: str) -> LoginUser:
    """There's no real user table — this is the one demo account, display
    fields derived deterministically from the username, not fabricated."""
    parts = username.replace(".", " ").replace("_", " ").split()
    initials = "".join(p[0] for p in parts[:2]).upper() or username[:2].upper()
    return LoginUser(
        name=username.title(),
        email=f"{username}@techmart.demo",
        role="Support Engineer (demo account)",
        initials=initials,
    )


@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
async def login_v1(request: Request, payload: LoginRequest):
    if not authenticate_demo_account(payload.username, payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    token = create_access_token(subject=payload.username)
    return LoginResponse(
        access_token=token,
        user=_derive_user(payload.username),
        expires_in=settings.jwt_expire_minutes * 60,
    )
