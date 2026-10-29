"""
Tests for the conversation history UI's backend support: session listing,
sorted by recency, with correct ownership isolation.
"""
import sys
import asyncio
sys.path.insert(0, ".")

from mongomock_motor import AsyncMongoMockClient

from database.conversations import append_message, list_sessions, ensure_indexes
from models.conversation import Message


def get_mock_db():
    client = AsyncMongoMockClient()
    return client["test_db"]


async def _test_list_sessions_returns_summaries():
    db = get_mock_db()
    await ensure_indexes(db)

    await append_message(db, "session-a", "vivek", Message(role="user", content="hello there"))
    await append_message(db, "session-a", "vivek", Message(role="assistant", content="hi, how can I help?"))

    sessions = await list_sessions(db, "vivek")
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == "session-a"
    assert sessions[0]["preview"] == "hi, how can I help?"  # last message, not first
    print("test_list_sessions_returns_summaries: PASS")


async def _test_list_sessions_sorted_by_most_recent_activity():
    db = get_mock_db()
    await ensure_indexes(db)

    await append_message(db, "session-old", "vivek", Message(role="user", content="first session"))
    await asyncio.sleep(0.01)
    await append_message(db, "session-new", "vivek", Message(role="user", content="second session"))

    sessions = await list_sessions(db, "vivek")
    assert sessions[0]["session_id"] == "session-new"
    assert sessions[1]["session_id"] == "session-old"
    print("test_list_sessions_sorted_by_most_recent_activity: PASS")


async def _test_updating_old_session_moves_it_to_top():
    """Sending a new message in an older session should bump it back to
    the top of the list, since sorting is by last activity, not creation."""
    db = get_mock_db()
    await ensure_indexes(db)

    await append_message(db, "session-1", "vivek", Message(role="user", content="msg 1"))
    await asyncio.sleep(0.01)
    await append_message(db, "session-2", "vivek", Message(role="user", content="msg 2"))
    await asyncio.sleep(0.01)
    await append_message(db, "session-1", "vivek", Message(role="user", content="msg 3 - back to session 1"))

    sessions = await list_sessions(db, "vivek")
    assert sessions[0]["session_id"] == "session-1"
    print("test_updating_old_session_moves_it_to_top: PASS")


async def _test_list_sessions_ownership_isolation():
    """A user must only see their own sessions, never another user's."""
    db = get_mock_db()
    await ensure_indexes(db)

    await append_message(db, "session-vivek", "vivek", Message(role="user", content="my message"))
    await append_message(db, "session-someone-else", "someone-else", Message(role="user", content="not yours"))

    sessions = await list_sessions(db, "vivek")
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == "session-vivek"
    print("test_list_sessions_ownership_isolation: PASS")


async def _test_empty_list_for_user_with_no_sessions():
    db = get_mock_db()
    await ensure_indexes(db)
    sessions = await list_sessions(db, "brand-new-user")
    assert sessions == []
    print("test_empty_list_for_user_with_no_sessions: PASS")


def test_sessions_endpoint_http_level():
    """Full HTTP-level test: create sessions via /chat, then confirm
    /chat/sessions lists them correctly for the right user only."""
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
    login = client.post("/auth/login", json={"username": "vivek", "password": "x"})
    token = login.json()["data"]["access_token"]

    r1 = client.post("/chat", json={"message": "store hours shipping"}, headers={"Authorization": f"Bearer {token}"})
    assert r1.status_code == 200

    sessions_resp = client.get("/chat/sessions", headers={"Authorization": f"Bearer {token}"})
    assert sessions_resp.status_code == 200
    sessions = sessions_resp.json()["data"]["sessions"]
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == r1.json()["data"]["session_id"]
    print("test_sessions_endpoint_http_level: PASS")

    # Unauthenticated request rejected
    r_noauth = client.get("/chat/sessions")
    assert r_noauth.status_code == 401
    print("test_sessions_endpoint_requires_auth: PASS")


if __name__ == "__main__":
    asyncio.run(_test_list_sessions_returns_summaries())
    asyncio.run(_test_list_sessions_sorted_by_most_recent_activity())
    asyncio.run(_test_updating_old_session_moves_it_to_top())
    asyncio.run(_test_list_sessions_ownership_isolation())
    asyncio.run(_test_empty_list_for_user_with_no_sessions())
    test_sessions_endpoint_http_level()
    print("\nAll conversation history / session listing tests passed.")
