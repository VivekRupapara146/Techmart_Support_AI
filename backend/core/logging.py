"""
Structured logging setup.

Every module should call `get_logger(__name__)` rather than configuring
its own logger — keeps output consistent and machine-parseable.

IMPORTANT: never log secrets (API keys, JWTs, passwords, full request bodies
that may contain PII). Log identifiers/metadata, not payloads.
"""
import logging
import sys
import json
from datetime import datetime, timezone

from core.config import settings


# Attributes every LogRecord carries by default. Anything on a record that is
# NOT in this set came from the caller's `extra={...}` and should be emitted.
_STANDARD_RECORD_ATTRS = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
) | {"message", "asctime", "taskName"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # Imported lazily to avoid a circular import (request_context doesn't
        # depend on logging, but keeping the import local here is cheap
        # insurance against future refactors creating one).
        from core.request_context import get_request_id

        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": get_request_id(),
            "message": record.getMessage(),
        }
        # Emit structured fields passed via `extra=`. Without this they are
        # silently dropped, so events like retrieval_logged never reach logs.
        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_ATTRS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        # default=str keeps logging from ever raising on a non-serializable value.
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())
    root.handlers = [handler]


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
