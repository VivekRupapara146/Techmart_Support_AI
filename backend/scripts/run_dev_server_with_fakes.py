"""
Runs the real FastAPI app with a mocked Mongo (mongomock-motor) and a fake
LLM/embedding-backed agent registry — no GEMINI_API_KEY or real MongoDB
needed. Two uses:

1. Local load testing (loadtest/locustfile.py) without burning real Gemini
   quota or needing cloud infra just to measure the app's own overhead
   (routing, retrieval, serialization, Mongo round-trips) — see
   loadtest/README.md for why that's a legitimate, disclosed thing to
   measure separately from upstream LLM latency.
2. Quick manual frontend-against-backend testing without setting up real
   credentials first.

Run from backend/: python -m scripts.run_dev_server_with_fakes
Then the API is at http://localhost:8000 exactly like a normal run.

NOT for anything resembling production — the "AI" responses are
deterministic canned text, not real model output.
"""
import sys
sys.path.insert(0, ".")

import os
os.environ.setdefault("JWT_SECRET_KEY", "dev-only-fake-server-secret-not-for-real-use-000")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGO_DB_NAME", "techmart_support_fake")
os.environ.setdefault("GEMINI_API_KEY", "")
os.environ.setdefault("ENVIRONMENT", "development")

import asyncio
import uvicorn
from mongomock_motor import AsyncMongoMockClient

import database.mongo as mongo_module
from database.conversations import ensure_indexes
import core.chat_pipeline as chat_pipeline
from agents.rag_agent import RAGAgent
from prompts.support_prompts import AGENT_SYSTEM_PROMPTS
from rag.ingestion import ingest_directory
from tests.fake_embeddings import FakeEmbeddingProvider, DIMENSION
from tests.fake_llm import FakeLLMProvider

import main  # noqa: E402  (imported after env vars are set, before app runs)


async def _noop() -> None:
    return None


def _wire_fakes() -> None:
    mock_db = AsyncMongoMockClient()["fake_db"]
    mongo_module._db = mock_db
    # main.py's lifespan calls connect_to_mongo()/close_mongo_connection()
    # for real on startup/shutdown — replace both with no-ops so it doesn't
    # try (and hang) dialing a real Mongo instance that doesn't exist here.
    mongo_module.connect_to_mongo = _noop
    mongo_module.close_mongo_connection = _noop
    main.connect_to_mongo = _noop
    main.close_mongo_connection = _noop

    async def _mock_is_healthy() -> bool:
        return True

    mongo_module.is_db_healthy = _mock_is_healthy
    import api.health as health_module
    import api.v1_health as v1_health_module
    health_module.is_db_healthy = _mock_is_healthy
    v1_health_module.is_db_healthy = _mock_is_healthy

    asyncio.run(ensure_indexes(mock_db))

    embedding_provider = FakeEmbeddingProvider()
    store = ingest_directory("knowledge_base", embedding_provider, embedding_dim=DIMENSION)
    registry = {
        name: RAGAgent(
            name=name, system_prompt=AGENT_SYSTEM_PROMPTS[name], llm=FakeLLMProvider(),
            embedding_provider=embedding_provider, store=store, confidence_threshold=0.0,
        )
        for name in ["billing", "technical", "product", "complaint", "faq"]
    }
    chat_pipeline.set_registry_for_tests(registry)
    print("Wired fake Mongo + fake LLM/embedding agent registry. Starting server...")


if __name__ == "__main__":
    _wire_fakes()
    uvicorn.run(main.app, host="0.0.0.0", port=8000)
