"""
Embedding provider abstraction.

Mirrors the LLM provider pattern from Milestone 0: the RAG pipeline depends
on this interface, not on Gemini directly, so it's swappable and so tests
can inject a fake provider instead of making real network calls.
"""
from abc import ABC, abstractmethod

from google import genai

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text, same order as input."""
        raise NotImplementedError


class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model: str = "gemini-embedding-001"):
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not set — cannot initialize GeminiEmbeddingProvider")
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = model

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            result = self._client.models.embed_content(model=self._model, contents=texts)
            return [e.values for e in result.embeddings]
        except Exception as exc:
            logger.error(f"Gemini embedding call failed: {exc}")
            raise
