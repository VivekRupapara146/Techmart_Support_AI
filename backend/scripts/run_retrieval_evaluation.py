"""
Runs the retrieval evaluation harness (eval/retrieval_eval.py) against the
real knowledge base using real Gemini embeddings — run this locally where
your GEMINI_API_KEY works (Gemini's API domain is network-blocked in the
sandbox this project was built in, same constraint noted in
scripts/evaluate_router_v2.py).

Run from backend/: python -m scripts.run_retrieval_evaluation
Produces: eval/retrieval_results.json, served by GET /v1/evaluation/summary
(api/v1_evaluation.py) alongside the router comparison.

Cost note: one Gemini embedding call per unique query (75 in the committed
dataset) plus the one-time knowledge-base ingestion (6 documents, chunked).
Comfortably inside Gemini's free tier in a single run.
"""
import sys
sys.path.insert(0, ".")

from rag.embeddings import GeminiEmbeddingProvider
from rag.ingestion import ingest_directory
from eval.retrieval_eval import evaluate_retrieval, save_results, print_summary


def main():
    embedding_provider = GeminiEmbeddingProvider()
    store = ingest_directory("knowledge_base", embedding_provider, embedding_dim=3072)

    results = evaluate_retrieval(embedding_provider, store)
    print_summary(results)
    save_results(results, "eval/retrieval_results.json")
    print("\nSaved to eval/retrieval_results.json — commit it so "
          "GET /v1/evaluation/summary can serve real hit@k/MRR/groundedness numbers.")


if __name__ == "__main__":
    main()
