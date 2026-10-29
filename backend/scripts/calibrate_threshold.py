"""
Retrieval confidence threshold calibration (Milestone 10 follow-up).

Runs REAL Gemini embeddings (not the fake test double) against the actual
knowledge base, using a small labeled query set: queries that SHOULD be
grounded (on-topic), queries that SHOULD trigger the honest fallback
(off-topic), and a few borderline cases to see where real scores actually
land. Prints a table of scores so we can pick a threshold based on the
real score distribution, not a guess.

Run from backend/: python -m scripts.calibrate_threshold
"""
import sys

from rag.embeddings import GeminiEmbeddingProvider
from rag.ingestion import ingest_directory
from rag.retrieval import retrieve

# Deliberately varied: on-topic queries per domain, clearly off-topic
# queries, and a few genuinely ambiguous/borderline ones.
ON_TOPIC_QUERIES = [
    "how do I get a refund for my order",
    "why is my Premium subscription still locked after payment",
    "what does the product warranty cover",
    "how do I escalate a complaint",
    "my device won't connect to wifi",
    "what are your store hours",
    "how long does shipping take",
    "how do I reset my password",
]

OFF_TOPIC_QUERIES = [
    "what's the weather like today",
    "who won the world cup",
    "can you write me a poem",
    "what is the capital of France",
    "tell me a joke",
]

BORDERLINE_QUERIES = [
    "do you sell smartphones",  # plausible-sounding but not in KB
    "can I speak to a human",  # tangentially related to complaint escalation
    "is there a mobile app",  # related to technical doc but not explicitly answered
]


def run_bucket(label, queries, embedding_provider, store):
    print(f"\n--- {label} ---")
    scores = []
    for q in queries:
        result = retrieve(q, embedding_provider, store, top_k=1)
        score = result.top_score
        scores.append(score)
        top_source = result.chunks[0]["source"] if result.chunks else "NONE"
        print(f"  {score:.4f}  [{top_source}]  {q}")
    if scores:
        print(f"  -> min={min(scores):.4f}  max={max(scores):.4f}  avg={sum(scores)/len(scores):.4f}")
    return scores


def main():
    print("Loading knowledge base and generating real Gemini embeddings...")
    embedding_provider = GeminiEmbeddingProvider()
    store = ingest_directory("knowledge_base", embedding_provider, embedding_dim=3072)
    print(f"Indexed {store._index.ntotal} chunks from the knowledge base.\n")

    on_scores = run_bucket("ON-TOPIC (should retrieve real content)", ON_TOPIC_QUERIES, embedding_provider, store)
    off_scores = run_bucket("OFF-TOPIC (should trigger honest fallback)", OFF_TOPIC_QUERIES, embedding_provider, store)
    border_scores = run_bucket("BORDERLINE (sanity check only)", BORDERLINE_QUERIES, embedding_provider, store)

    print("\n=== SUMMARY ===")
    if on_scores and off_scores:
        min_on = min(on_scores)
        max_off = max(off_scores)
        print(f"Lowest on-topic score:  {min_on:.4f}")
        print(f"Highest off-topic score: {max_off:.4f}")
        if min_on > max_off:
            suggested = round((min_on + max_off) / 2, 3)
            print(f"Clean separation exists. Suggested threshold (midpoint): {suggested}")
        else:
            print(
                "WARNING: on-topic and off-topic score ranges OVERLAP. "
                "There's no single threshold that cleanly separates them — "
                "paste this full output back so we can look at it together "
                "rather than picking a number that will misclassify some queries."
            )
    print("\nBorderline scores are for context only — use judgment, not just the number.")


if __name__ == "__main__":
    main()
