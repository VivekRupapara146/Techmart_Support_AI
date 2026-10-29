"""
Per-request correlation ID.

Every request gets a UUID (or reuses an inbound X-Request-ID, so requests can
be traced across a reverse proxy / load balancer that already assigns one).
It's stashed in a ContextVar so any code on the call stack — log lines, error
responses, telemetry — can read it without threading it through every
function signature, and echoed back as a response header so the frontend can
show it (the UI's "traceId" field) and a person reporting a bug can hand it
back to you.
"""
import uuid
from contextvars import ContextVar
from typing import Callable, Awaitable

from fastapi import Request, Response

REQUEST_ID_HEADER = "X-Request-ID"

_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    return _request_id_ctx.get()


async def request_id_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    incoming = request.headers.get(REQUEST_ID_HEADER)
    request_id = incoming if incoming else uuid.uuid4().hex
    token = _request_id_ctx.set(request_id)
    try:
        response = await call_next(request)
    finally:
        _request_id_ctx.reset(token)
    response.headers[REQUEST_ID_HEADER] = request_id
    return response
