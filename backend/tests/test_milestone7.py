"""
Tests for Milestone 7 — Router v2b (trained classifier).

Unlike v2's tests, this uses the REAL trained artifact (already fully
offline/local, no network dependency once trained) rather than a fake —
these are the actual accuracy characteristics of the shipped model.
"""
import sys
sys.path.insert(0, ".")

from router.trained_classifier import route
from router.types import VALID_AGENTS
from ml.banking77_mapping import BANKING77_TO_DOMAIN


def test_mapping_covers_all_77_categories_exactly():
    """Sanity check the mapping module itself, independent of training —
    catches a typo even if no one re-runs training."""
    assert len(BANKING77_TO_DOMAIN) == 77
    assert all(v in VALID_AGENTS for v in BANKING77_TO_DOMAIN.values())
    print("test_mapping_covers_all_77_categories_exactly: PASS")


def test_model_artifact_loads_and_predicts():
    decision = route("I was charged twice for the same purchase")
    assert decision.agents[0] in VALID_AGENTS
    assert decision.confidence == "trained_classifier"
    print(f"test_model_artifact_loads_and_predicts: PASS (predicted={decision.agents})")


def test_billing_query_routes_to_billing():
    decision = route("I want a refund for a transaction I was charged twice for")
    assert decision.agents == ["billing"]
    print("test_billing_query_routes_to_billing: PASS")


def test_technical_query_routes_to_technical():
    decision = route("my card is not working and I forgot my PIN")
    assert decision.agents == ["technical"]
    print("test_technical_query_routes_to_technical: PASS")


def test_complaint_query_routes_to_complaint():
    decision = route("someone stole my card and I think it's compromised")
    assert decision.agents == ["complaint"]
    print("test_complaint_query_routes_to_complaint: PASS")


def test_single_label_only_never_multi_agent():
    """Documents the disclosed limitation: v2b always returns exactly one
    agent, unlike v1/v2 which can return several."""
    decision = route("I paid but my card is also not working and I'm furious about it")
    assert len(decision.agents) == 1
    print(f"test_single_label_only_never_multi_agent: PASS (chose {decision.agents[0]} among overlapping signals)")


if __name__ == "__main__":
    test_mapping_covers_all_77_categories_exactly()
    test_model_artifact_loads_and_predicts()
    test_billing_query_routes_to_billing()
    test_technical_query_routes_to_technical()
    test_complaint_query_routes_to_complaint()
    test_single_label_only_never_multi_agent()
    print("\nAll Milestone 7 tests passed.")
