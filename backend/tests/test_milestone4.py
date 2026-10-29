"""
Tests for Milestone 4 — all 5 domain agents built generically, and a
multi-agent /chat query that exercises real aggregation (not just the
single-agent passthrough tested in Milestone 3).
"""
import sys
sys.path.insert(0, ".")

from router.rule_based import AGENT_KEYWORDS
from agents.rag_agent import RAGAgent
from prompts.support_prompts import AGENT_SYSTEM_PROMPTS
from rag.ingestion import ingest_directory
from tests.fake_embeddings import FakeEmbeddingProvider, DIMENSION
from tests.fake_llm import FakeLLMProvider


def build_test_registry():
    embedding_provider = FakeEmbeddingProvider()
    store = ingest_directory("knowledge_base", embedding_provider, embedding_dim=DIMENSION)
    return {
        name: RAGAgent(
            name=name,
            system_prompt=AGENT_SYSTEM_PROMPTS[name],
            llm=FakeLLMProvider(),
            embedding_provider=embedding_provider,
            store=store,
            confidence_threshold=0.3,
        )
        for name in AGENT_KEYWORDS.keys()
    }


def test_all_five_agents_exist_and_respond():
    registry = build_test_registry()
    assert set(registry.keys()) == {"billing", "technical", "product", "complaint", "faq"}

    for name, agent in registry.items():
        response = agent.respond("test query about general topic")
        assert response.agent_name == name
        assert isinstance(response.text, str) and len(response.text) > 0
    print("test_all_five_agents_exist_and_respond: PASS")


def test_product_agent_grounds_on_warranty_doc():
    registry = build_test_registry()
    response = registry["product"].respond("warranty claim serial number proof of purchase extended warranty")
    assert response.grounded is True
    print("test_product_agent_grounds_on_warranty_doc: PASS")


def test_complaint_agent_grounds_on_escalation_doc():
    registry = build_test_registry()
    response = registry["complaint"].respond("complaint escalation account manager")
    assert response.grounded is True
    print("test_complaint_agent_grounds_on_escalation_doc: PASS")


def test_technical_agent_grounds_on_technical_troubleshooting_doc():
    registry = build_test_registry()
    response = registry["technical"].respond("bluetooth pairing device firmware update")
    assert response.grounded is True
    print("test_technical_agent_grounds_on_technical_troubleshooting_doc: PASS")


def test_faq_agent_grounds_on_general_faq_doc():
    registry = build_test_registry()
    response = registry["faq"].respond("store hours shipping tracking order account")
    assert response.grounded is True
    print("test_faq_agent_grounds_on_general_faq_doc: PASS")


def test_multi_agent_chat_end_to_end():
    """
    Exercises the real multi-agent aggregation path (not the single-agent
    passthrough M3 tested) using the classic M0 example query.
    """
    import asyncio
    from fastapi.testclient import TestClient
    from mongomock_motor import AsyncMongoMockClient
    import main
    import core.chat_pipeline as chat_module
    import database.mongo as mongo_module
    from database.conversations import ensure_indexes

    mock_db = AsyncMongoMockClient()["test_db"]
    mongo_module._db = mock_db
    asyncio.run(ensure_indexes(mock_db))

    chat_module._registry = build_test_registry()
    client = TestClient(main.app)

    login = client.post("/auth/login", json={"username": "vivek", "password": "test123"})
    token = login.json()["data"]["access_token"]

    r = client.post(
        "/chat",
        json={"message": "I paid yesterday but Premium is still locked with a login error"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert set(data["routed_agents"]) >= {"billing", "technical"}
    assert "On billing" in data["reply"]
    assert "On the technical issue" in data["reply"]
    print(f"test_multi_agent_chat_end_to_end: PASS (agents={data['routed_agents']})")


if __name__ == "__main__":
    test_all_five_agents_exist_and_respond()
    test_product_agent_grounds_on_warranty_doc()
    test_complaint_agent_grounds_on_escalation_doc()
    test_technical_agent_grounds_on_technical_troubleshooting_doc()
    test_faq_agent_grounds_on_general_faq_doc()
    test_multi_agent_chat_end_to_end()
    print("\nAll Milestone 4 tests passed.")
