"""
Generic RAG-grounded agent. All 5 domains (FAQ, Billing, Technical, Product,
Complaint) currently share the same knowledge base and retrieval logic —
only the name (for aggregator labeling) and system prompt persona differ.
Avoids 5 near-duplicate agent classes (Instruction 6).

KNOWN LIMITATION: retrieval is domain-filtered via rag/domain_sources.py,
not per-agent separate indices — see that module's docstring.
"""
import time

from agents.base_agent import BaseAgent, AgentResponse
from llm.provider import LLMProvider, LLMResult
from rag.embeddings import EmbeddingProvider
from rag.vector_store import VectorStore
from rag.retrieval import retrieve, CONFIDENCE_THRESHOLD
from rag.domain_sources import get_allowed_sources
from prompts.support_prompts import INSUFFICIENT_CONTEXT_FALLBACK, build_rag_prompt
from core.logging import get_logger

logger = get_logger(__name__)

EVIDENCE_SNIPPET_CHARS = 240

# GeminiLLMProvider already retries/backs off/times out and degrades
# internally (llm/provider.py) — but a RAG agent may be wired to *any*
# LLMProvider (tests inject fakes; a future provider might not implement its
# own degrade path), so this is a second, provider-agnostic safety net:
# whatever goes wrong in generate_with_meta, the chat endpoint gets a
# graceful AgentResponse back, never an unhandled exception / 500.
AGENT_LEVEL_FALLBACK_MESSAGE = (
    "Something went wrong answering that on our end. Please try again in a moment."
)


class RAGAgent(BaseAgent):
    def __init__(
        self,
        name: str,
        system_prompt: str,
        llm: LLMProvider,
        embedding_provider: EmbeddingProvider,
        store: VectorStore,
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
    ):
        self.name = name
        self._system_prompt = system_prompt
        self._llm = llm
        self._embedding_provider = embedding_provider
        self._store = store
        self._confidence_threshold = confidence_threshold
        # None means "no domain mapping, search everything" — a graceful
        # fallback, not a silent failure, if a new domain is ever added
        # without updating rag/domain_sources.py.
        self._allowed_sources = get_allowed_sources(name)

    def respond(self, query: str) -> AgentResponse:
        retrieval_start = time.perf_counter()
        result = retrieve(
            query, self._embedding_provider, self._store,
            confidence_threshold=self._confidence_threshold,
            allowed_sources=self._allowed_sources,
        )
        retrieval_latency_ms = (time.perf_counter() - retrieval_start) * 1000

        if result.insufficient_context:
            return AgentResponse(
                agent_name=self.name,
                text=INSUFFICIENT_CONTEXT_FALLBACK,
                grounded=False,
                evidence=_evidence_from_chunks(result.chunks),
                retrieval_latency_ms=retrieval_latency_ms,
            )

        prompt = build_rag_prompt(query, result.chunks)
        try:
            llm_result = self._llm.generate_with_meta(prompt, system_prompt=self._system_prompt)
        except Exception as exc:
            logger.error(f"LLM call raised for agent={self.name!r}, degrading gracefully: {exc}")
            llm_result = LLMResult(
                text=AGENT_LEVEL_FALLBACK_MESSAGE, tokens_in=None, tokens_out=None,
                latency_ms=0.0, retries=0, model="unknown", degraded=True,
            )

        return AgentResponse(
            agent_name=self.name,
            text=llm_result.text,
            # Degraded (Gemini unreachable after retries) is never "grounded" —
            # the fallback apology wasn't generated from the retrieved context.
            grounded=not llm_result.degraded,
            evidence=_evidence_from_chunks(result.chunks),
            tokens_in=llm_result.tokens_in,
            tokens_out=llm_result.tokens_out,
            retrieval_latency_ms=retrieval_latency_ms,
            latency_ms=llm_result.latency_ms,
            degraded=llm_result.degraded,
        )


def _evidence_from_chunks(chunks: list[dict]) -> list[dict]:
    """Real retrieved chunks, not fabricated citations — straight from the
    FAISS search result (rag/vector_store.py), truncated for display."""
    return [
        {
            "source": c["source"],
            "chunk_index": c.get("chunk_index"),
            "similarity": round(c["score"], 4),
            "snippet": c["text"][:EVIDENCE_SNIPPET_CHARS],
        }
        for c in chunks
    ]
