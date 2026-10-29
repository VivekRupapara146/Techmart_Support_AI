"""
Chunking strategy: fixed-size word-count windows with overlap.

We approximate tokens by word count (~0.75 words per token for English is
the usual rule of thumb) rather than pulling in a tokenizer tied to a
specific model family — Gemini doesn't publish a public tiktoken-compatible
tokenizer, so an exact token count isn't available offline. This is a
documented approximation, not a precision guarantee; it's good enough for
chunk sizing, not for hard TPM budgeting.
"""
from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    chunk_index: int
    source: str


def chunk_text(text: str, source: str, chunk_size_words: int = 375, overlap_words: int = 40) -> list[Chunk]:
    """
    Split text into overlapping word-count windows.

    chunk_size_words=375 approximates ~500 tokens.
    overlap_words=40 approximates ~50 tokens, preserving context across chunk boundaries.
    """
    if chunk_size_words <= overlap_words:
        raise ValueError("chunk_size_words must be greater than overlap_words")

    words = text.split()
    if not words:
        return []

    chunks: list[Chunk] = []
    start = 0
    index = 0
    step = chunk_size_words - overlap_words

    while start < len(words):
        window = words[start:start + chunk_size_words]
        chunks.append(Chunk(text=" ".join(window), chunk_index=index, source=source))
        index += 1
        start += step

    return chunks
