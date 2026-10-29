"""
LLM provider abstraction. Agents depend on this interface, not on Gemini
directly — swappable to another provider later as a config change (M0
decision).

Reliability: GeminiLLMProvider wraps every call with a timeout (a hung HTTP
call must not hang a request forever) and bounded retries with exponential
backoff + jitter (so a single transient 429/503 from Gemini doesn't surface
as a 500 to the user). If every retry is exhausted, it degrades to a fixed
apology message instead of raising — callers get `LLMResult.degraded=True`
and can decide how to handle that (RAGAgent marks the response ungrounded
rather than pretending the model answered).
"""
import random
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass

from google import genai

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

BASE_BACKOFF_SECONDS = 0.5

# One shared pool for all Gemini calls in this process. The google-genai
# client call is synchronous (blocking) under the hood; running it in a
# worker thread is what lets us enforce a hard wall-clock timeout around it
# (Python has no way to time out a plain blocking call in-thread).
_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="llm-call")


@dataclass
class LLMResult:
    text: str
    tokens_in: int | None
    tokens_out: int | None
    latency_ms: float
    retries: int
    model: str
    degraded: bool = False  # True => `text` is the fallback apology, not a real model response


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        raise NotImplementedError

    def generate_with_meta(self, prompt: str, system_prompt: str | None = None) -> LLMResult:
        """Default implementation: times generate() but has no real token-usage
        or retry data. Test fakes (FakeLLMProvider, ScriptedLLMProvider, ...)
        get this for free without needing to implement it themselves.
        GeminiLLMProvider overrides this with real retry/backoff/usage data."""
        start = time.perf_counter()
        text = self.generate(prompt, system_prompt=system_prompt)
        latency_ms = (time.perf_counter() - start) * 1000
        return LLMResult(
            text=text, tokens_in=None, tokens_out=None,
            latency_ms=latency_ms, retries=0, model="unknown",
        )


class GeminiLLMProvider(LLMProvider):
    FALLBACK_MESSAGE = (
        "Our AI assistant is temporarily unavailable right now (the model provider "
        "isn't responding). Please try again in a moment, or rephrase your question."
    )

    def __init__(
        self,
        model: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
    ):
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not set — cannot initialize GeminiLLMProvider")
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = model or settings.gemini_chat_model
        self._timeout_seconds = timeout_seconds or settings.llm_timeout_seconds
        self._max_retries = max_retries or settings.llm_max_retries

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        return self.generate_with_meta(prompt, system_prompt=system_prompt).text

    def _call_once(self, prompt: str, system_prompt: str | None):
        config = {"system_instruction": system_prompt} if system_prompt else {}
        return self._client.models.generate_content(model=self._model, contents=prompt, config=config)

    def generate_with_meta(self, prompt: str, system_prompt: str | None = None) -> LLMResult:
        start = time.perf_counter()
        last_exc: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                future = _executor.submit(self._call_once, prompt, system_prompt)
                response = future.result(timeout=self._timeout_seconds)

                usage = getattr(response, "usage_metadata", None)
                tokens_in = getattr(usage, "prompt_token_count", None) if usage else None
                tokens_out = getattr(usage, "candidates_token_count", None) if usage else None

                return LLMResult(
                    text=response.text,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    latency_ms=(time.perf_counter() - start) * 1000,
                    retries=attempt - 1,
                    model=self._model,
                )
            except FutureTimeoutError as exc:
                last_exc = exc
                logger.warning(
                    f"Gemini call timed out after {self._timeout_seconds}s "
                    f"(attempt {attempt}/{self._max_retries})"
                )
            except Exception as exc:
                last_exc = exc
                logger.warning(f"Gemini call failed (attempt {attempt}/{self._max_retries}): {exc}")

            if attempt < self._max_retries:
                backoff = BASE_BACKOFF_SECONDS * (2 ** (attempt - 1)) + random.uniform(0, 0.25)
                time.sleep(backoff)

        logger.error(f"Gemini call exhausted {self._max_retries} attempts, degrading: {last_exc}")
        return LLMResult(
            text=self.FALLBACK_MESSAGE,
            tokens_in=None,
            tokens_out=None,
            latency_ms=(time.perf_counter() - start) * 1000,
            retries=self._max_retries,
            model=self._model,
            degraded=True,
        )
