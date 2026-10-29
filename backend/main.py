"""
Application entrypoint.

Wires together: config, logging, DB lifecycle, rate limiting,
global error handling, and route registration.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware

from core.config import settings
from core.logging import configure_logging, get_logger
from core.rate_limit import limiter
from core.request_context import request_id_middleware
from core.security_startup import verify_production_secrets
from database.mongo import connect_to_mongo, close_mongo_connection, get_db
from database.conversations import ensure_indexes
from models.response import APIResponse
from api.health import router as health_router
from auth.routes import router as auth_router
from api.chat import router_ as chat_router
from api.v1_auth import router as v1_auth_router
from api.v1_chat import router as v1_chat_router
from api.v1_health import router as v1_health_router
from api.v1_evaluation import router as v1_evaluation_router

configure_logging()
logger = get_logger(__name__)
verify_production_secrets()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.app_name} ({settings.environment})")
    await connect_to_mongo()
    await ensure_indexes(get_db())
    yield
    await close_mongo_connection()
    logger.info("Shutdown complete")


app = FastAPI(title=settings.app_name, lifespan=lifespan)

# Rate limiting — SlowAPIMiddleware is what actually makes `default_limits`
# apply to every route automatically. Without it, only routes with an
# explicit @limiter.limit(...) decorator were ever enforced (a real gap
# found during the Milestone 9 security audit — /auth/login had zero
# rate limiting despite RATE_LIMIT_DEFAULT being configured).
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS — explicit allowlist, never "*", since credentials (Bearer tokens)
# are involved. Configured via env so the frontend's real origin can be
# added without a code change.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


# Per-request correlation ID — every log line and the X-Request-ID response
# header share it, so one request can be traced end-to-end. Registered last
# so it's the OUTERMOST middleware (Starlette runs middleware in reverse
# registration order) and the ID is already set before CORS/security-headers/
# rate-limit middleware (and their log lines) run.
app.middleware("http")(request_id_middleware)

# Routes — unprefixed routers are kept for backward compatibility with the
# original Milestone test suite; /v1/* is the real, versioned contract the
# frontend speaks (see api/v1_*.py). Both share the same underlying
# core/chat_pipeline.py logic so they can't drift apart.
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(v1_health_router, prefix="/v1")
app.include_router(v1_auth_router, prefix="/v1")
app.include_router(v1_chat_router, prefix="/v1")
app.include_router(v1_evaluation_router, prefix="/v1")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch-all: never leak stack traces to the client (Instruction 9).
    Full detail goes to server-side logs only.
    """
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=APIResponse(
            success=False, error="An unexpected error occurred. Please try again later."
        ).model_dump(),
    )
