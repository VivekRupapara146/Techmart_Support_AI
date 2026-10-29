"""
Tests for structured logging.

Regression guard for a real bug: JsonFormatter used to drop every field
passed via `extra=`, so events such as `retrieval_logged` (scores, sources)
never reached the logs even though evaluation depends on them.
"""
import io
import json
import logging
import sys
sys.path.insert(0, ".")

from core.logging import JsonFormatter
from rag.ingestion import ingest_directory
from rag.retrieval import retrieve
from router.rule_based import route
from tests.fake_embeddings import FakeEmbeddingProvider, DIMENSION


def _capture(logger_name: str):
    """Attach a JsonFormatter handler to a logger; return (stream, cleanup)."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger(logger_name)
    previous_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    def cleanup():
        logger.removeHandler(handler)
        logger.setLevel(previous_level)

    return stream, cleanup


def _lines(stream: io.StringIO) -> list[dict]:
    return [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]


def test_extra_fields_are_emitted():
    stream, cleanup = _capture("test_logging_extra")
    try:
        logging.getLogger("test_logging_extra").info("evt", extra={"top_score": 0.7, "agents": ["billing"]})
    finally:
        cleanup()
    record = _lines(stream)[0]
    assert record["top_score"] == 0.7
    assert record["agents"] == ["billing"]
    assert record["message"] == "evt"
    print("test_extra_fields_are_emitted: PASS")


def test_standard_attributes_are_not_leaked():
    stream, cleanup = _capture("test_logging_std")
    try:
        logging.getLogger("test_logging_std").info("plain message")
    finally:
        cleanup()
    record = _lines(stream)[0]
    # request_id is always present (it's the per-request correlation ID from
    # core/request_context.py, "-" outside a request) — an intentional
    # standard field, not a leaked LogRecord attribute.
    assert set(record) == {"timestamp", "level", "logger", "message", "request_id"}, \
        f"unexpected keys: {set(record)}"
    print("test_standard_attributes_are_not_leaked: PASS")


def test_non_serializable_extra_does_not_raise():
    stream, cleanup = _capture("test_logging_unser")
    try:
        logging.getLogger("test_logging_unser").info("evt", extra={"obj": object()})
    finally:
        cleanup()
    assert "obj" in _lines(stream)[0]
    print("test_non_serializable_extra_does_not_raise: PASS")


def test_retrieval_event_logged_without_raw_query():
    provider = FakeEmbeddingProvider()
    store = ingest_directory("knowledge_base", provider, embedding_dim=DIMENSION)
    secret_query = "refund for card ending 4242 for jane@example.com"

    stream, cleanup = _capture("rag.retrieval")
    try:
        retrieve(secret_query, provider, store, top_k=2)
    finally:
        cleanup()

    record = next(r for r in _lines(stream) if r["message"] == "retrieval_logged")
    assert "top_score" in record and "chunk_sources" in record, "retrieval data must reach the logs"
    assert record["query_length"] == len(secret_query)
    assert "query" not in record
    assert "jane@example.com" not in json.dumps(record), "raw user text must not be logged"
    print("test_retrieval_event_logged_without_raw_query: PASS")


def test_route_event_logged_without_raw_query():
    secret_query = "refund to jane@example.com"
    stream, cleanup = _capture("router.rule_based")
    try:
        route(secret_query)
    finally:
        cleanup()

    record = next(r for r in _lines(stream) if r["message"] == "route_decision_logged")
    assert "agents" in record and "query" not in record
    assert "jane@example.com" not in json.dumps(record)
    print("test_route_event_logged_without_raw_query: PASS")


if __name__ == "__main__":
    test_extra_fields_are_emitted()
    test_standard_attributes_are_not_leaked()
    test_non_serializable_extra_does_not_raise()
    test_retrieval_event_logged_without_raw_query()
    test_route_event_logged_without_raw_query()
    print("\nAll logging tests passed.")
