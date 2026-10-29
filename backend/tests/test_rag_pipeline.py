"""
Tests for the Milestone 2 RAG pipeline.

Uses FakeEmbeddingProvider throughout (no network dependency), so this
suite runs anywhere, including CI, without a Gemini API key.
"""
import sys
sys.path.insert(0, ".")

from rag.chunking import chunk_text
from rag.ingestion import ingest_directory
from rag.retrieval import retrieve
from tests.fake_embeddings import FakeEmbeddingProvider, DIMENSION


def test_chunking_positive():
    text = "word " * 1000
    chunks = chunk_text(text, source="test.txt", chunk_size_words=375, overlap_words=40)
    assert len(chunks) > 1, "long text should split into multiple chunks"
    assert chunks[0].chunk_index == 0
    print("test_chunking_positive: PASS")


def test_chunking_empty_text():
    chunks = chunk_text("", source="empty.txt")
    assert chunks == [], "empty text should produce zero chunks"
    print("test_chunking_empty_text: PASS")


def test_chunking_invalid_params():
    try:
        chunk_text("some text", source="x.txt", chunk_size_words=10, overlap_words=10)
        print("test_chunking_invalid_params: FAIL (should have raised)")
    except ValueError:
        print("test_chunking_invalid_params: PASS")


def test_ingestion_and_retrieval_relevant_query():
    provider = FakeEmbeddingProvider()
    store = ingest_directory("knowledge_base", provider, embedding_dim=DIMENSION)

    result = retrieve("refund payment method original", provider, store, top_k=2)
    assert len(result.chunks) > 0
    assert result.chunks[0]["source"] == "refund_policy.txt", (
        f"expected refund_policy.txt to rank first, got {result.chunks[0]['source']}"
    )
    print(f"test_ingestion_and_retrieval_relevant_query: PASS (top_score={result.top_score:.3f})")


def test_retrieval_insufficient_context_fallback():
    provider = FakeEmbeddingProvider()
    store = ingest_directory("knowledge_base", provider, embedding_dim=DIMENSION)

    # Query with zero word overlap with either doc -> low similarity -> fallback should trigger
    result = retrieve("zzqx flibber wozzle nonexistent gibberish", provider, store, top_k=2)
    assert result.insufficient_context is True, "unrelated query should trigger insufficient_context fallback"
    print("test_retrieval_insufficient_context_fallback: PASS")


def test_retrieval_empty_store():
    from rag.vector_store import VectorStore
    provider = FakeEmbeddingProvider()
    empty_store = VectorStore(dimension=DIMENSION)
    result = retrieve("any query", provider, empty_store, top_k=3)
    assert result.chunks == []
    assert result.insufficient_context is True
    print("test_retrieval_empty_store: PASS")


def test_vector_store_save_and_load(tmp_dir="./tmp_test_store"):
    import shutil
    from rag.vector_store import VectorStore

    provider = FakeEmbeddingProvider()
    store = ingest_directory("knowledge_base", provider, embedding_dim=DIMENSION)
    store.save(tmp_dir)

    reloaded = VectorStore.load(tmp_dir)
    result = retrieve("premium subscription locked payment", provider, reloaded, top_k=2)
    assert len(result.chunks) > 0

    shutil.rmtree(tmp_dir)
    print("test_vector_store_save_and_load: PASS")


if __name__ == "__main__":
    test_chunking_positive()
    test_chunking_empty_text()
    test_chunking_invalid_params()
    test_ingestion_and_retrieval_relevant_query()
    test_retrieval_insufficient_context_fallback()
    test_retrieval_empty_store()
    test_vector_store_save_and_load()
    print("\nAll RAG pipeline tests passed.")
