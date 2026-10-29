"""
Tests for Milestone 3 — router, FAQ agent, aggregator, and the /chat endpoint.
Uses fake LLM/embedding providers throughout, no network dependency.
"""
import sys
sys.path.insert(0, ".")

from router.rule_based import route, DEFAULT_AGENT, AGENT_KEYWORDS
from agents.rag_agent import RAGAgent
from agents.base_agent import AgentResponse
from prompts.support_prompts import AGENT_SYSTEM_PROMPTS
from aggregator import aggregate
from rag.ingestion import ingest_directory
from tests.fake_embeddings import FakeEmbeddingProvider, DIMENSION
from tests.fake_llm import FakeLLMProvider


# --- Router tests -----------------------------------------------------------

def test_router_single_match():
    decision = route("I was charged twice for my invoice")
    assert "billing" in decision.agents
    print("test_router_single_match: PASS")


def test_router_multi_match():
    decision = route("I paid yesterday but Premium is still locked with a login error")
    assert "billing" in decision.agents
    assert "technical" in decision.agents
    print(f"test_router_multi_match: PASS (agents={decision.agents})")


def test_router_zero_match_defaults_to_faq():
    decision = route("asdkjasdkj random gibberish query")
    assert decision.agents == [DEFAULT_AGENT]
    print("test_router_zero_match_defaults_to_faq: PASS")


# --- FAQ agent tests ----------------------------------------------------------

def test_faq_agent_grounded_response():
    embedding_provider = FakeEmbeddingProvider()
    store = ingest_directory("knowledge_base", embedding_provider, embedding_dim=DIMENSION)
    agent = RAGAgent(name="faq", system_prompt=AGENT_SYSTEM_PROMPTS["faq"], llm=FakeLLMProvider(), embedding_provider=embedding_provider, store=store, confidence_threshold=0.3)

    response = agent.respond("store hours shipping tracking order account")
    assert response.grounded is True
    assert "FAKE_LLM_RESPONSE" in response.text
    print("test_faq_agent_grounded_response: PASS")


def test_faq_agent_insufficient_context_fallback():
    embedding_provider = FakeEmbeddingProvider()
    store = ingest_directory("knowledge_base", embedding_provider, embedding_dim=DIMENSION)
    agent = RAGAgent(name="faq", system_prompt=AGENT_SYSTEM_PROMPTS["faq"], llm=FakeLLMProvider(), embedding_provider=embedding_provider, store=store, confidence_threshold=0.3)

    response = agent.respond("zzqx flibber wozzle nonexistent gibberish")
    assert response.grounded is False
    assert "don't have enough information" in response.text
    print("test_faq_agent_insufficient_context_fallback: PASS")


# --- Aggregator tests ---------------------------------------------------------

def test_aggregator_single_response_passthrough():
    responses = [AgentResponse(agent_name="faq", text="Here's your answer.", grounded=True)]
    result = aggregate(responses)
    assert result == "Here's your answer."
    print("test_aggregator_single_response_passthrough: PASS")


def test_aggregator_multi_response_merge():
    responses = [
        AgentResponse(agent_name="billing", text="Refund processed.", grounded=True),
        AgentResponse(agent_name="technical", text="Try logging out and back in.", grounded=True),
    ]
    result = aggregate(responses)
    assert "On billing" in result
    assert "On the technical issue" in result
    print("test_aggregator_multi_response_merge: PASS")


def test_aggregator_empty_responses():
    result = aggregate([])
    assert "wasn't able to find an agent" in result
    print("test_aggregator_empty_responses: PASS")


# --- End-to-end /chat endpoint test (dependency-injected fakes) --------------

def test_chat_endpoint_end_to_end():
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

    embedding_provider = FakeEmbeddingProvider()
    store = ingest_directory("knowledge_base", embedding_provider, embedding_dim=DIMENSION)
    fake_registry = {"faq": RAGAgent(name="faq", system_prompt=AGENT_SYSTEM_PROMPTS["faq"], llm=FakeLLMProvider(), embedding_provider=embedding_provider, store=store, confidence_threshold=0.3)}

    # Override the lazy registry builder so no real Gemini call happens
    chat_module._registry = fake_registry

    client = TestClient(main.app)

    login = client.post("/auth/login", json={"username": "vivek", "password": "test123"})
    token = login.json()["data"]["access_token"]

    r = client.post(
        "/chat",
        json={"message": "how do I get a refund on my order"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert "faq" in data["routed_agents"] or "billing" in data["routed_agents"]
    print(f"test_chat_endpoint_end_to_end: PASS (routed_agents={data['routed_agents']})")

    # Negative: no auth token -> 401
    r2 = client.post("/chat", json={"message": "hello"})
    assert r2.status_code == 401
    print("test_chat_endpoint_no_auth_rejected: PASS")

    # Negative: empty message -> 422
    r3 = client.post(
        "/chat", json={"message": ""}, headers={"Authorization": f"Bearer {token}"}
    )
    assert r3.status_code == 422
    print("test_chat_endpoint_empty_message_rejected: PASS")


if __name__ == "__main__":
    test_router_single_match()
    test_router_multi_match()
    test_router_zero_match_defaults_to_faq()
    test_faq_agent_grounded_response()
    test_faq_agent_insufficient_context_fallback()
    test_aggregator_single_response_passthrough()
    test_aggregator_multi_response_merge()
    test_aggregator_empty_responses()
    test_chat_endpoint_end_to_end()
    print("\nAll Milestone 3 tests passed.")
