"""
Retrieval evaluation harness — measures what the router comparison harness
(eval/harness.py) doesn't: whether FAISS retrieval itself is any good, and
whether the confidence-threshold fallback (rag/retrieval.py) correctly
refuses on out-of-KB questions instead of answering from irrelevant chunks.

Metrics, all computed directly from retrieve() — the exact function
production uses, not a re-implementation of it:

- hit@k (k=1,3,5): for in-KB questions, whether a chunk from an expected
  source document appears in the top-k retrieved results. The standard
  retrieval-quality metric.
- MRR@5: mean reciprocal rank of the first correct chunk within the top 5.
  Rewards ranking the right answer first, not just "somewhere in top 5".
- grounded_retrieval_rate: for in-KB questions, the fraction where the
  system would actually answer (top_score >= CONFIDENCE_THRESHOLD) AND
  would answer from the right document. This is NOT an LLM-hallucination
  judge — that would need a real generation call per case and a separate
  judge call, which costs real API quota and time this capstone doesn't
  need to spend. It's a stricter, honest proxy: "retrieved the right thing
  with enough confidence to use it."
- true_refusal_rate: for out-of-KB questions, the fraction where
  insufficient_context correctly fired (the system refuses rather than
  answering from irrelevant content).
- false_refusal_rate: for in-KB questions, the fraction where
  insufficient_context incorrectly fired on a question that WAS answerable
  (a real cost — a frustrated user told "I don't know" about something in
  the knowledge base).
"""
import json
import time
from dataclasses import asdict, dataclass

from rag.embeddings import EmbeddingProvider
from rag.vector_store import VectorStore
from rag.retrieval import retrieve, CONFIDENCE_THRESHOLD
from eval.retrieval_dataset import RETRIEVAL_EVAL_DATASET, RetrievalEvalCase


@dataclass
class RetrievalCaseResult:
    query: str
    category: str
    expected_sources: list[str]
    retrieved_sources: list[str]  # top-5, in rank order
    top_score: float
    insufficient_context: bool
    hit_at_1: bool
    hit_at_3: bool
    hit_at_5: bool
    reciprocal_rank: float  # 0.0 if no correct source in top 5
    latency_ms: float


def _reciprocal_rank(retrieved_sources: list[str], expected_sources: set[str]) -> float:
    for rank, source in enumerate(retrieved_sources, start=1):
        if source in expected_sources:
            return 1.0 / rank
    return 0.0


def evaluate_retrieval(
    embedding_provider: EmbeddingProvider,
    store: VectorStore,
    dataset: list[RetrievalEvalCase] = RETRIEVAL_EVAL_DATASET,
    confidence_threshold: float = CONFIDENCE_THRESHOLD,
    top_k: int = 5,
) -> dict:
    results: list[RetrievalCaseResult] = []

    for case in dataset:
        start = time.perf_counter()
        # allowed_sources=None: tests raw retrieval quality across the whole
        # KB, not domain-filtered per-agent retrieval (rag/domain_sources.py
        # is a separate, already-tested concern).
        outcome = retrieve(
            case.query, embedding_provider, store,
            top_k=top_k, confidence_threshold=confidence_threshold, allowed_sources=None,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        retrieved_sources = [c["source"] for c in outcome.chunks]
        expected = set(case.expected_sources)

        results.append(RetrievalCaseResult(
            query=case.query,
            category=case.category,
            expected_sources=case.expected_sources,
            retrieved_sources=retrieved_sources,
            top_score=outcome.top_score,
            insufficient_context=outcome.insufficient_context,
            hit_at_1=bool(expected & set(retrieved_sources[:1])),
            hit_at_3=bool(expected & set(retrieved_sources[:3])),
            hit_at_5=bool(expected & set(retrieved_sources[:5])),
            reciprocal_rank=_reciprocal_rank(retrieved_sources, expected) if expected else 0.0,
            latency_ms=elapsed_ms,
        ))

    return _summarize(results)


def _summarize(results: list[RetrievalCaseResult]) -> dict:
    in_kb = [r for r in results if r.category == "in_kb"]
    out_of_kb = [r for r in results if r.category == "out_of_kb"]
    n_in_kb = len(in_kb) or 1  # guard against division by zero on a malformed dataset
    n_out_of_kb = len(out_of_kb) or 1

    grounded_and_correct = sum(
        1 for r in in_kb if not r.insufficient_context and r.hit_at_1
    )

    return {
        "n_cases": len(results),
        "n_in_kb": len(in_kb),
        "n_out_of_kb": len(out_of_kb),
        "retrieval": {
            "hit_at_1": sum(r.hit_at_1 for r in in_kb) / n_in_kb,
            "hit_at_3": sum(r.hit_at_3 for r in in_kb) / n_in_kb,
            "hit_at_5": sum(r.hit_at_5 for r in in_kb) / n_in_kb,
            "mrr_at_5": sum(r.reciprocal_rank for r in in_kb) / n_in_kb,
            "avg_latency_ms": sum(r.latency_ms for r in results) / len(results) if results else 0.0,
        },
        "groundedness": {
            # Of in-KB questions, how often the system would both answer
            # (pass the confidence threshold) AND cite the right document.
            "grounded_retrieval_rate": grounded_and_correct / n_in_kb,
        },
        "refusal": {
            "true_refusal_rate": sum(r.insufficient_context for r in out_of_kb) / n_out_of_kb,
            "false_refusal_rate": sum(r.insufficient_context for r in in_kb) / n_in_kb,
        },
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "cases": [asdict(r) for r in results],
    }


def save_results(results: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)


def print_summary(results: dict) -> None:
    print(f"\n=== Retrieval evaluation ({results['n_cases']} cases: "
          f"{results['n_in_kb']} in-KB, {results['n_out_of_kb']} out-of-KB) ===")
    r = results["retrieval"]
    print(f"  hit@1:            {r['hit_at_1']:.1%}")
    print(f"  hit@3:            {r['hit_at_3']:.1%}")
    print(f"  hit@5:            {r['hit_at_5']:.1%}")
    print(f"  MRR@5:            {r['mrr_at_5']:.3f}")
    print(f"  Avg latency:      {r['avg_latency_ms']:.2f} ms")
    print(f"  Grounded rate:    {results['groundedness']['grounded_retrieval_rate']:.1%} "
          f"(answered AND cited the right document)")
    print(f"  True refusal:     {results['refusal']['true_refusal_rate']:.1%} "
          f"(correctly refused out-of-KB questions)")
    print(f"  False refusal:    {results['refusal']['false_refusal_rate']:.1%} "
          f"(incorrectly refused answerable questions — lower is better)")
