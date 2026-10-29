"""
Deterministic fake embedding provider for tests.

Uses simple word-overlap-weighted hashing so semantically similar text
(shared words) produces similar vectors, without any network call or real
embedding model. This lets the retrieval/vector-store logic be tested for
correctness independent of Gemini's availability.

NOT for production use — swap for GeminiEmbeddingProvider at runtime.
"""
import hashlib
import numpy as np

from rag.embeddings import EmbeddingProvider

DIMENSION = 64


class FakeEmbeddingProvider(EmbeddingProvider):
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        vec = np.zeros(DIMENSION, dtype="float32")
        words = text.lower().split()
        for word in words:
            h = int(hashlib.md5(word.encode()).hexdigest(), 16)
            idx = h % DIMENSION
            vec[idx] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()
