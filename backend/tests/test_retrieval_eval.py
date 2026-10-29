"""
Tests for eval/retrieval_eval.py's metric arithmetic — hit@k, MRR@5,
grounded_retrieval_rate, true/false refusal rate — against a hand-built
VectorStore with known, exact cosine similarities (2D unit vectors at
chosen angles), so every expected number is computable by hand rather than
"looks about right". No embedding model involved: a scripted provider maps
each known query string straight to its pre-chosen vector.

This tests the HARNESS's correctness, not retrieval quality against the
real knowledge base — that needs real Gemini embeddings and is run
separately via scripts/run_retrieval_evaluation.py (see that file's
docstring for why it can't run in this sandbox).
"""
import sys
import math

sys.path.insert(0, ".")

from rag.embeddings import EmbeddingProvider
from rag.vector_store import VectorStore
from eval.retrieval_eval import evaluate_retrieval
from eval.retrieval_dataset import RetrievalEvalCase


def _unit_vector(angle_deg: float) -> list[float]:
    rad = math.radians(angle_deg)
    return [math.cos(rad), math.sin(rad)]


class ScriptedEmbeddingProvider(EmbeddingProvider):
    """Maps each known query string to a pre-chosen 2D vector. Every
    evaluate_retrieval() call embeds the query exactly once, so this is a
    1:1 lookup, not a batch — matches how retrieve() calls .embed([query])."""
    def __init__(self, vector_for_query: dict[str, list[float]]):
        self._map = vector_for_query

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._map[t] for t in texts]


def _build_store(chunks: list[tuple[str, float]]) -> VectorStore:
    """chunks: list of (source, angle_deg) — one chunk per entry, angle
    relative to the query vector at 0deg."""
    store = VectorStore(dimension=2)
    vectors = [_unit_vector(angle) for _, angle in chunks]
    metadata = [{"source": source, "chunk_index": 0, "text": f"chunk from {source}"} for source, _ in chunks]
    store.add(vectors, metadata)
    return store


def test_hit_at_1_and_mrr_when_correct_source_ranks_first():
    query = "q1"
    store = _build_store([
        ("correct.txt", 0),     # cos(0)   = 1.0
        ("other1.txt", 30),     # cos(30)  = 0.866
        ("other2.txt", 45),     # cos(45)  = 0.707
        ("other3.txt", 60),     # cos(60)  = 0.5
        ("other4.txt", 80),     # cos(80)  = 0.174
    ])
    embedder = ScriptedEmbeddingProvider({query: _unit_vector(0)})
    dataset = [RetrievalEvalCase(query=query, expected_sources=["correct.txt"], category="in_kb")]

    results = evaluate_retrieval(embedder, store, dataset=dataset, confidence_threshold=0.3)

    assert results["retrieval"]["hit_at_1"] == 1.0
    assert results["retrieval"]["hit_at_3"] == 1.0
    assert results["retrieval"]["hit_at_5"] == 1.0
    assert results["retrieval"]["mrr_at_5"] == 1.0
    assert results["groundedness"]["grounded_retrieval_rate"] == 1.0
    print("test_hit_at_1_and_mrr_when_correct_source_ranks_first: PASS")


def test_hit_at_3_but_not_hit_at_1_when_correct_source_ranks_third():
    query = "q2"
    store = _build_store([
        ("decoy1.txt", 5),      # cos(5)  = 0.996  <- rank 1, wrong doc
        ("decoy2.txt", 15),     # cos(15) = 0.966  <- rank 2, wrong doc
        ("target.txt", 25),     # cos(25) = 0.906  <- rank 3, CORRECT doc
        ("decoy3.txt", 70),     # cos(70) = 0.342
        ("decoy4.txt", 89),     # cos(89) = 0.017
    ])
    embedder = ScriptedEmbeddingProvider({query: _unit_vector(0)})
    dataset = [RetrievalEvalCase(query=query, expected_sources=["target.txt"], category="in_kb")]

    results = evaluate_retrieval(embedder, store, dataset=dataset, confidence_threshold=0.3)

    assert results["retrieval"]["hit_at_1"] == 0.0
    assert results["retrieval"]["hit_at_3"] == 1.0
    assert results["retrieval"]["hit_at_5"] == 1.0
    assert abs(results["retrieval"]["mrr_at_5"] - (1 / 3)) < 1e-9
    # Grounded rate requires hit@1, not just hit@5 — this case misses it,
    # even though retrieval technically found the right doc eventually.
    assert results["groundedness"]["grounded_retrieval_rate"] == 0.0
    print("test_hit_at_3_but_not_hit_at_1_when_correct_source_ranks_third: PASS")


def test_out_of_kb_query_correctly_refuses():
    query = "q3"
    # Every chunk is far from the query (max similarity ~0.17) — nothing in
    # the KB is relevant, which is exactly what an out-of-KB question should
    # look like.
    store = _build_store([("some_doc.txt", 80), ("other_doc.txt", 85)])
    embedder = ScriptedEmbeddingProvider({query: _unit_vector(0)})
    dataset = [RetrievalEvalCase(query=query, expected_sources=[], category="out_of_kb")]

    results = evaluate_retrieval(embedder, store, dataset=dataset, confidence_threshold=0.3)

    assert results["refusal"]["true_refusal_rate"] == 1.0
    print("test_out_of_kb_query_correctly_refuses: PASS")


def test_in_kb_query_below_threshold_counts_as_false_refusal():
    query = "q4"
    # Correct doc IS retrieved (it's the only chunk) but similarity is too
    # low to clear the confidence threshold — the system would wrongly
    # refuse a question it actually has the answer to.
    store = _build_store([("target.txt", 80)])  # cos(80) = 0.174
    embedder = ScriptedEmbeddingProvider({query: _unit_vector(0)})
    dataset = [RetrievalEvalCase(query=query, expected_sources=["target.txt"], category="in_kb")]

    results = evaluate_retrieval(embedder, store, dataset=dataset, confidence_threshold=0.3)

    assert results["retrieval"]["hit_at_1"] == 1.0  # retrieval found it...
    assert results["refusal"]["false_refusal_rate"] == 1.0  # ...but confidence gate blocks it
    assert results["groundedness"]["grounded_retrieval_rate"] == 0.0  # not grounded: never answered
    print("test_in_kb_query_below_threshold_counts_as_false_refusal: PASS")


def test_mixed_dataset_denominators_are_per_category_not_pooled():
    """2 in-KB cases (1 hit, 1 miss) + 1 out-of-KB case — hit@1 must average
    over the 2 in-KB cases only (0.5), not over all 3. (Refusal correctness
    itself is covered by the two dedicated tests above; this one is purely
    about the denominators not leaking across categories.)"""
    store = _build_store([("a.txt", 0), ("b.txt", 85)])
    embedder = ScriptedEmbeddingProvider({
        "hit": _unit_vector(0),     # closely matches a.txt -> hit
        "miss": _unit_vector(90),   # closer to b.txt than a.txt -> miss (wrong doc, not unanswered)
        "out_of_kb_q": _unit_vector(45),  # just present to populate the out_of_kb bucket
    })
    dataset = [
        RetrievalEvalCase(query="hit", expected_sources=["a.txt"], category="in_kb"),
        RetrievalEvalCase(query="miss", expected_sources=["a.txt"], category="in_kb"),
        RetrievalEvalCase(query="out_of_kb_q", expected_sources=[], category="out_of_kb"),
    ]

    results = evaluate_retrieval(embedder, store, dataset=dataset, confidence_threshold=0.3)

    assert results["n_in_kb"] == 2
    assert results["n_out_of_kb"] == 1
    assert results["retrieval"]["hit_at_1"] == 0.5
    print("test_mixed_dataset_denominators_are_per_category_not_pooled: PASS")


if __name__ == "__main__":
    test_hit_at_1_and_mrr_when_correct_source_ranks_first()
    test_hit_at_3_but_not_hit_at_1_when_correct_source_ranks_third()
    test_out_of_kb_query_correctly_refuses()
    test_in_kb_query_below_threshold_counts_as_false_refusal()
    test_mixed_dataset_denominators_are_per_category_not_pooled()
    print("\nAll retrieval eval harness tests passed.")
