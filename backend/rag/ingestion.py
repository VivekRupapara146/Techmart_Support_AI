"""
Ingestion pipeline: reads .txt/.md files from a directory, chunks them,
embeds each chunk, and builds a VectorStore.

Kept deliberately format-simple for Milestone 2 (.txt/.md only). PDF
ingestion for real TechMart docs can be added later via the pdf skill
without touching this module's structure.
"""
from pathlib import Path

from rag.chunking import chunk_text
from rag.embeddings import EmbeddingProvider
from rag.vector_store import VectorStore
from core.logging import get_logger

logger = get_logger(__name__)

SUPPORTED_EXTENSIONS = {".txt", ".md"}


def ingest_directory(directory: str, embedding_provider: EmbeddingProvider, embedding_dim: int) -> VectorStore:
    doc_dir = Path(directory)
    if not doc_dir.exists():
        raise FileNotFoundError(f"Knowledge base directory not found: {directory}")

    files = [p for p in doc_dir.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS]
    if not files:
        logger.warning(f"No supported documents found in {directory}")

    store = VectorStore(dimension=embedding_dim)

    for file_path in files:
        text = file_path.read_text(encoding="utf-8")
        chunks = chunk_text(text, source=file_path.name)
        if not chunks:
            continue

        vectors = embedding_provider.embed([c.text for c in chunks])
        metadata = [{"text": c.text, "source": c.source, "chunk_index": c.chunk_index} for c in chunks]
        store.add(vectors, metadata)
        logger.info(f"Ingested {file_path.name}: {len(chunks)} chunks")

    return store
