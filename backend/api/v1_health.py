"""
Versioned health endpoint.

Deliberately simpler than the frontend's OperationsView mockup (which shows
a multi-node cluster, Redis eviction stats, replica lag, etc.) — this is a
single FastAPI process talking to a single Mongo instance with an in-process
FAISS index, and every field below is really measured, not invented to look
like a bigger deployment than it is. See the README's "what's real vs
illustrative" note; OperationsView's cluster-theatre fields are left as a
known follow-up to trim in the UI rather than faked here.
"""
import time

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from core.config import settings
from core.chat_pipeline import get_vector_store_count
from database.mongo import is_db_healthy

router = APIRouter(prefix="/health", tags=["health (v1)"])

_process_start = time.monotonic()


class ServiceHealth(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    name: str
    status: str  # "connected" | "disconnected" | "not_warmed_up"
    detail: str


class HealthResponseV1(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    status: str  # "operational" | "degraded"
    version: str
    git_commit: str
    environment: str
    uptime_seconds: float
    services: dict[str, ServiceHealth]


@router.get("", response_model=HealthResponseV1)
async def health_v1():
    db_ok = await is_db_healthy()
    vector_count = get_vector_store_count()

    services = {
        "fastapi": ServiceHealth(name="FastAPI", status="connected", detail="process is responding"),
        "mongodb": ServiceHealth(
            name="MongoDB", status="connected" if db_ok else "disconnected",
            detail="ping succeeded" if db_ok else "ping failed or not connected",
        ),
        "faiss": ServiceHealth(
            name="FAISS (in-process vector index)",
            status="connected" if vector_count is not None else "not_warmed_up",
            detail=(
                f"{vector_count} vectors indexed" if vector_count is not None
                else "not yet built — becomes ready on first chat request"
            ),
        ),
    }

    return HealthResponseV1(
        status="operational" if db_ok else "degraded",
        version=settings.app_version,
        git_commit=settings.git_commit_sha,
        environment=settings.environment,
        uptime_seconds=round(time.monotonic() - _process_start, 1),
        services=services,
    )
