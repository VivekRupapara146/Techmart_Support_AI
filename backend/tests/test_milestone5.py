"""
Tests for Milestone 5 — conversation memory/sessions.
Uses mongomock-motor (in-memory, async-compatible) so this runs without a
real MongoDB instance.
"""
import sys
import asyncio
sys.path.insert(0, ".")

from mongomock_motor import AsyncMongoMockClient

from database.conversations import append_message, get_history, ensure_indexes, MAX_MESSAGES_PER_SESSION
from models.conversation import Message


def get_mock_db():
    client = AsyncMongoMockClient()
    return client["test_db"]


async def _test_append_and_retrieve():
    db = get_mock_db()
    await ensure_indexes(db)

    await append_message(db, "session-1", "vivek", Message(role="user", content="hello"))
    await append_message(db, "session-1", "vivek", Message(role="assistant", content="hi there"))

    history = await get_history(db, "session-1", "vivek")
    assert history is not None
    assert len(history) == 2
    assert history[0].content == "hello"
    assert history[1].content == "hi there"
    print("test_append_and_retrieve: PASS")


async def _test_ownership_isolation():
    """A different user must NOT be able to read someone else's session."""
    db = get_mock_db()
    await ensure_indexes(db)

    await append_message(db, "session-2", "vivek", Message(role="user", content="private message"))

    history_as_owner = await get_history(db, "session-2", "vivek")
    assert history_as_owner is not None

    history_as_stranger = await get_history(db, "session-2", "someone-else")
    assert history_as_stranger is None
    print("test_ownership_isolation: PASS")


async def _test_nonexistent_session_returns_none():
    db = get_mock_db()
    await ensure_indexes(db)
    result = await get_history(db, "does-not-exist", "vivek")
    assert result is None
    print("test_nonexistent_session_returns_none: PASS")


async def _test_message_cap_enforced():
    db = get_mock_db()
    await ensure_indexes(db)

    for i in range(MAX_MESSAGES_PER_SESSION + 10):
        await append_message(db, "session-3", "vivek", Message(role="user", content=f"msg {i}"))

    history = await get_history(db, "session-3", "vivek")
    assert len(history) == MAX_MESSAGES_PER_SESSION
    # Should keep the MOST RECENT messages, not the oldest
    assert history[-1].content == f"msg {MAX_MESSAGES_PER_SESSION + 9}"
    print(f"test_message_cap_enforced: PASS (capped at {MAX_MESSAGES_PER_SESSION})")


def test_chat_endpoint_persists_and_history_endpoint_retrieves():
    """Full HTTP-level test: chat -> persisted -> history endpoint returns it,
    and a second user cannot read the first user's history."""
    from fastapi.testclient import TestClient
    import main
    import core.chat_pipeline as chat_module
    import database.mongo as mongo_module
    from agents.rag_agent import RAGAgent
    from prompts.support_prompts import AGENT_SYSTEM_PROMPTS
    from rag.ingestion import ingest_directory
    from tests.fake_embeddings import FakeEmbeddingProvider, DIMENSION
    from tests.fake_llm import FakeLLMProvider
    from router.rule_based import AGENT_KEYWORDS

    # Swap in the mock DB and fake agent registry
    mock_db = get_mock_db()
    mongo_module._db = mock_db
    asyncio.run(ensure_indexes(mock_db))

    embedding_provider = FakeEmbeddingProvider()
    store = ingest_directory("knowledge_base", embedding_provider, embedding_dim=DIMENSION)
    chat_module._registry = {
        name: RAGAgent(
            name=name, system_prompt=AGENT_SYSTEM_PROMPTS[name], llm=FakeLLMProvider(),
            embedding_provider=embedding_provider, store=store, confidence_threshold=0.3,
        )
        for name in AGENT_KEYWORDS.keys()
    }

    client = TestClient(main.app)

    login1 = client.post("/auth/login", json={"username": "user1", "password": "x"})
    token1 = login1.json()["data"]["access_token"]

    r = client.post(
        "/chat", json={"message": "refund payment original method"},
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert r.status_code == 200, r.text
    session_id = r.json()["data"]["session_id"]

    hist = client.get(f"/chat/history/{session_id}", headers={"Authorization": f"Bearer {token1}"})
    assert hist.status_code == 200, hist.text
    messages = hist.json()["data"]["messages"]
    assert len(messages) == 2  # user + assistant
    print("test_chat_persists_history: PASS")

    # Negative: a different user requesting the same session_id -> 404, not leaked
    login2 = client.post("/auth/login", json={"username": "user2", "password": "x"})
    token2 = login2.json()["data"]["access_token"]
    hist2 = client.get(f"/chat/history/{session_id}", headers={"Authorization": f"Bearer {token2}"})
    assert hist2.status_code == 404
    print("test_chat_history_cross_user_blocked: PASS")

    # Negative: malformed session_id rejected
    bad = client.get("/chat/history/../../etc-passwd", headers={"Authorization": f"Bearer {token1}"})
    assert bad.status_code in (404, 422)
    print("test_chat_history_malformed_session_id_rejected: PASS")


if __name__ == "__main__":
    asyncio.run(_test_append_and_retrieve())
    asyncio.run(_test_ownership_isolation())
    asyncio.run(_test_nonexistent_session_returns_none())
    asyncio.run(_test_message_cap_enforced())
    test_chat_endpoint_persists_and_history_endpoint_retrieves()
    print("\nAll Milestone 5 tests passed.")
