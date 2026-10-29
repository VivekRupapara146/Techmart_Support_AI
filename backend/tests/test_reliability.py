"""
Tests for the reliability layer added on top of the original milestones:
Gemini retry/backoff/timeout + graceful degrade (llm/provider.py), the
agent-level safety net on top of that (agents/rag_agent.py), and the
per-request correlation ID (core/request_context.py).

No real network calls — GeminiLLMProvider's __init__ (which requires
GEMINI_API_KEY and builds a real genai.Client) is bypassed via
object.__new__ + manual attribute assignment, and only _call_once is
overridden to simulate transient failures/timeouts deterministically.
"""
import sys
import time

sys.path.insert(0, ".")

from llm.provider import GeminiLLMProvider, LLMResult, LLMProvider
from agents.rag_agent import RAGAgent, AGENT_LEVEL_FALLBACK_MESSAGE
from prompts.support_prompts import AGENT_SYSTEM_PROMPTS
from rag.ingestion import ingest_directory
from tests.fake_embeddings import FakeEmbeddingProvider, DIMENSION


class _FakeResponse:
    def __init__(self, text: str):
        self.text = text
        self.usage_metadata = None


def _make_probe(fail_times: int, max_retries: int = 3, timeout_seconds: float = 5.0, raise_cls=RuntimeError):
    """A GeminiLLMProvider whose constructor and real API call are bypassed —
    only the retry/backoff/degrade logic in generate_with_meta is under test."""
    probe = object.__new__(GeminiLLMProvider)
    probe._model = "test-model"
    probe._timeout_seconds = timeout_seconds
    probe._max_retries = max_retries
    probe._calls = 0

    def _call_once(prompt, system_prompt):
        probe._calls += 1
        if probe._calls <= fail_times:
            raise raise_cls("simulated transient failure")
        return _FakeResponse("real answer")

    probe._call_once = _call_once
    return probe


def test_succeeds_on_first_try_no_retry_overhead():
    probe = _make_probe(fail_times=0)
    result = probe.generate_with_meta("prompt")
    assert result.text == "real answer"
    assert result.retries == 0
    assert result.degraded is False
    print("test_succeeds_on_first_try_no_retry_overhead: PASS")


def test_transient_failure_then_success_is_recovered_via_retry():
    probe = _make_probe(fail_times=2, max_retries=3)
    start = time.perf_counter()
    result = probe.generate_with_meta("prompt")
    elapsed = time.perf_counter() - start
    assert result.text == "real answer"
    assert result.retries == 2
    assert result.degraded is False
    # Backoff is exponential (0.5s, 1.0s base + jitter) — sanity check we
    # actually waited rather than hot-looping, without being flaky about
    # the exact jitter.
    assert elapsed >= 1.0, f"expected backoff delay, elapsed only {elapsed:.3f}s"
    print(f"test_transient_failure_then_success_is_recovered_via_retry: PASS (elapsed={elapsed:.2f}s)")


def test_exhausted_retries_degrades_instead_of_raising():
    probe = _make_probe(fail_times=99, max_retries=3)
    result = probe.generate_with_meta("prompt")
    assert result.degraded is True
    assert result.text == GeminiLLMProvider.FALLBACK_MESSAGE
    assert result.retries == 3
    print("test_exhausted_retries_degrades_instead_of_raising: PASS")


def test_generate_never_raises_even_when_exhausted():
    """The public .generate() method (used by the router) must also never
    raise — it just returns the fallback text."""
    probe = _make_probe(fail_times=99, max_retries=2)
    text = probe.generate(prompt="prompt")
    assert text == GeminiLLMProvider.FALLBACK_MESSAGE
    print("test_generate_never_raises_even_when_exhausted: PASS")


class _AlwaysRaisingProvider(LLMProvider):
    """A non-Gemini LLMProvider that doesn't implement its own degrade logic
    — exercises the RAGAgent-level safety net, not the Gemini-specific one."""
    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        raise RuntimeError("this provider has no retry logic of its own")


def test_rag_agent_degrades_gracefully_when_provider_raises():
    embedding_provider = FakeEmbeddingProvider()
    store = ingest_directory("knowledge_base", embedding_provider, embedding_dim=DIMENSION)
    agent = RAGAgent(
        name="faq",
        system_prompt=AGENT_SYSTEM_PROMPTS["faq"],
        llm=_AlwaysRaisingProvider(),
        embedding_provider=embedding_provider,
        store=store,
        confidence_threshold=0.0,  # force past the insufficient-context branch
    )
    response = agent.respond("what are your store hours")
    assert response.grounded is False
    assert response.degraded is True
    assert response.text == AGENT_LEVEL_FALLBACK_MESSAGE
    print("test_rag_agent_degrades_gracefully_when_provider_raises: PASS")


def test_request_id_middleware_echoes_and_generates():
    import main
    from fastapi.testclient import TestClient

    client = TestClient(main.app)

    # No inbound ID -> one is generated.
    r1 = client.get("/health")
    assert "X-Request-ID" in r1.headers and len(r1.headers["X-Request-ID"]) > 0

    # Inbound ID -> echoed back unchanged, so a caller's own trace ID survives.
    r2 = client.get("/health", headers={"X-Request-ID": "caller-supplied-id-123"})
    assert r2.headers["X-Request-ID"] == "caller-supplied-id-123"

    print("test_request_id_middleware_echoes_and_generates: PASS")


if __name__ == "__main__":
    test_succeeds_on_first_try_no_retry_overhead()
    test_transient_failure_then_success_is_recovered_via_retry()
    test_exhausted_retries_degrades_instead_of_raising()
    test_generate_never_raises_even_when_exhausted()
    test_rag_agent_degrades_gracefully_when_provider_raises()
    test_request_id_middleware_echoes_and_generates()
    print("\nAll reliability tests passed.")
