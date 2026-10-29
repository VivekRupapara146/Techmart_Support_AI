"""
Health check endpoint — no auth required.
Verifies the app is running and the database is reachable.
"""
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from database.mongo import is_db_healthy
from models.response import APIResponse

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    db_ok = await is_db_healthy()

    if not db_ok:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=APIResponse(
                success=False, error="Database unreachable"
            ).model_dump(),
        )

    return APIResponse(success=True, data={"status": "ok", "database": "connected"})
