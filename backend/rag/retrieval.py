"""
Retrieval with a confidence-threshold fallback.

Enforces the M0 decision (Instruction 17 — no ungrounded answers): if the
best retrieved chunk's similarity score is below CONFIDENCE_THRESHOLD, we
signal insufficient_context=True so the calling agent can respond honestly
rather than letting the LLM improvise from weak or irrelevant context.

Every retrieval logs which chunks were returned and their scores, so
Milestone 10 (evaluation) has real data instead of having to guess.
"""
from dataclasses import dataclass, field

from rag.embeddings import EmbeddingProvider
from rag.vector_store import VectorStore
from core.logging import get_logger

logger = get_logger(__name__)

CONFIDENCE_THRESHOLD = 0.51
# Calibrated (Milestone 10 follow-up) against REAL Gemini embeddings using
# scripts/calibrate_threshold.py, not guessed. Data: 8 on-topic queries
# scored 0.5325-0.7564; 5 off-topic queries scored 0.4374-0.4913. This
# value sits in that gap. The previous placeholder (0.55) was too high —
# it would have wrongly rejected at least one genuinely answerable query
# ("how do I reset my password", scored 0.5325) as insufficient context.
# Small sample (8/5 queries against a 6-doc KB) — re-run the calibration
# script if the knowledge base grows substantially.


@dataclass
class RetrievalResult:
    query: str
    chunks: list[dict]
    insufficient_context: bool
    top_score: float = field(default=0.0)


def retrieve(
    query: str,
    embedding_provider: EmbeddingProvider,
    store: VectorStore,
    top_k: int = 4,
    confidence_threshold: float = CONFIDENCE_THRESHOLD,
    allowed_sources: set[str] | None = None,
) -> RetrievalResult:
    query_vector = embedding_provider.embed([query])[0]
    chunks = store.search(query_vector, top_k=top_k, allowed_sources=allowed_sources)

    top_score = chunks[0]["score"] if chunks else 0.0
    insufficient = top_score < confidence_threshold

    logger.info(
        "retrieval_logged",
        extra={
            # Length only, never the raw text: user queries may contain PII.
            "query_length": len(query),
            "top_score": top_score,
            "insufficient_context": insufficient,
            "chunk_sources": [c["source"] for c in chunks],
        },
    )

    return RetrievalResult(query=query, chunks=chunks, insufficient_context=insufficient, top_score=top_score)
