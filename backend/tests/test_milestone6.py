"""
Tests for Milestone 6 — Router v2 (LLM-based), including the defensive
fallback-to-v1 path on malformed output or API failure.
"""
import sys
sys.path.insert(0, ".")

from router.llm_based import route
from router.types import VALID_AGENTS
from tests.scripted_llm import ScriptedLLMProvider, RaisingLLMProvider


def test_valid_json_single_agent():
    llm = ScriptedLLMProvider('{"agents": ["billing"]}')
    decision = route("I was charged twice", llm)
    assert decision.agents == ["billing"]
    assert decision.confidence == "llm_based"
    print("test_valid_json_single_agent: PASS")


def test_valid_json_multi_agent():
    llm = ScriptedLLMProvider('{"agents": ["billing", "technical"]}')
    decision = route("paid but still locked with login error", llm)
    assert set(decision.agents) == {"billing", "technical"}
    assert decision.confidence == "llm_based"
    print("test_valid_json_multi_agent: PASS")


def test_json_wrapped_in_markdown_fences_still_parses():
    llm = ScriptedLLMProvider('```json\n{"agents": ["product"]}\n```')
    decision = route("is this compatible with my laptop", llm)
    assert decision.agents == ["product"]
    print("test_json_wrapped_in_markdown_fences_still_parses: PASS")


def test_invalid_agent_name_dropped_not_passed_through():
    """The model hallucinating a category that doesn't exist must never
    reach the agent registry as a real routing target."""
    llm = ScriptedLLMProvider('{"agents": ["billing", "made_up_category"]}')
    decision = route("test query", llm)
    assert decision.agents == ["billing"]
    assert all(a in VALID_AGENTS for a in decision.agents)
    print("test_invalid_agent_name_dropped_not_passed_through: PASS")


def test_malformed_json_falls_back_to_rule_based():
    llm = ScriptedLLMProvider("this is not json at all")
    decision = route("I need a refund for my invoice", llm)
    assert decision.confidence == "llm_based_fallback_to_rule_based"
    assert "billing" in decision.agents  # rule-based keyword match still works
    print("test_malformed_json_falls_back_to_rule_based: PASS")


def test_all_invalid_agent_names_falls_back():
    llm = ScriptedLLMProvider('{"agents": ["not_real", "also_not_real"]}')
    decision = route("refund my invoice", llm)
    assert decision.confidence == "llm_based_fallback_to_rule_based"
    print("test_all_invalid_agent_names_falls_back: PASS")


def test_llm_api_failure_falls_back_gracefully():
    """If the Gemini call itself throws (network error, rate limit), routing
    must not crash the request — it should fall back to v1."""
    llm = RaisingLLMProvider()
    decision = route("I need a refund", llm)
    assert decision.confidence == "llm_based_fallback_to_rule_based"
    assert "billing" in decision.agents
    print("test_llm_api_failure_falls_back_gracefully: PASS")


def test_empty_agents_list_falls_back():
    llm = ScriptedLLMProvider('{"agents": []}')
    decision = route("random query", llm)
    assert decision.confidence == "llm_based_fallback_to_rule_based"
    print("test_empty_agents_list_falls_back: PASS")


if __name__ == "__main__":
    test_valid_json_single_agent()
    test_valid_json_multi_agent()
    test_json_wrapped_in_markdown_fences_still_parses()
    test_invalid_agent_name_dropped_not_passed_through()
    test_malformed_json_falls_back_to_rule_based()
    test_all_invalid_agent_names_falls_back()
    test_llm_api_failure_falls_back_gracefully()
    test_empty_agents_list_falls_back()
    print("\nAll Milestone 6 tests passed.")
