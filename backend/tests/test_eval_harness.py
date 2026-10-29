"""
Tests for the Milestone 10 evaluation harness — verifying the metrics
computation itself is correct, using controlled fake routers with known,
hand-calculated expected outcomes.
"""
import sys
sys.path.insert(0, ".")

from eval.harness import evaluate_router
from eval.dataset import EvalCase


def test_perfect_router_scores_100_percent():
    dataset = [
        EvalCase("q1", ["billing"], "clean_single"),
        EvalCase("q2", ["technical", "billing"], "clean_multi"),
    ]
    perfect_router = lambda q: {"q1": ["billing"], "q2": ["technical", "billing"]}[q]
    result = evaluate_router("perfect", perfect_router, dataset)
    assert result["overall"]["exact_match_rate"] == 1.0
    assert result["overall"]["hit_rate"] == 1.0
    assert result["overall"]["avg_precision"] == 1.0
    print("test_perfect_router_scores_100_percent: PASS")


def test_always_wrong_router_scores_0_percent():
    dataset = [EvalCase("q1", ["billing"], "clean_single")]
    wrong_router = lambda q: ["product"]
    result = evaluate_router("wrong", wrong_router, dataset)
    assert result["overall"]["exact_match_rate"] == 0.0
    assert result["overall"]["hit_rate"] == 0.0
    assert result["overall"]["avg_precision"] == 0.0
    print("test_always_wrong_router_scores_0_percent: PASS")


def test_partial_multi_label_hit_scores_correctly():
    """Predicting {billing, product} when the truth is {billing, technical}
    should hit (billing overlaps) but not exact-match, with 50% precision."""
    dataset = [EvalCase("q1", ["billing", "technical"], "clean_multi")]
    partial_router = lambda q: ["billing", "product"]
    result = evaluate_router("partial", partial_router, dataset)
    assert result["overall"]["exact_match_rate"] == 0.0
    assert result["overall"]["hit_rate"] == 1.0
    assert result["overall"]["avg_precision"] == 0.5
    print("test_partial_multi_label_hit_scores_correctly: PASS")


def test_single_label_router_cannot_exact_match_multi_label_truth():
    """Documents v2b's real structural limitation: predicting one correct
    agent out of a two-agent truth set can hit, but never exact-match."""
    dataset = [EvalCase("q1", ["billing", "technical"], "clean_multi")]
    single_label_router = lambda q: ["billing"]
    result = evaluate_router("single_label", single_label_router, dataset)
    assert result["overall"]["exact_match_rate"] == 0.0
    assert result["overall"]["hit_rate"] == 1.0
    print("test_single_label_router_cannot_exact_match_multi_label_truth: PASS")


def test_empty_prediction_scores_zero_precision_not_a_crash():
    dataset = [EvalCase("q1", ["billing"], "clean_single")]
    empty_router = lambda q: []
    result = evaluate_router("empty", empty_router, dataset)
    assert result["overall"]["avg_precision"] == 0.0
    assert result["overall"]["hit_rate"] == 0.0
    print("test_empty_prediction_scores_zero_precision_not_a_crash: PASS")


def test_category_breakdown_sums_correctly():
    dataset = [
        EvalCase("q1", ["billing"], "clean_single"),
        EvalCase("q2", ["billing"], "clean_single"),
        EvalCase("q3", ["billing"], "clean_multi"),
    ]
    router = lambda q: ["billing"] if q != "q2" else ["product"]
    result = evaluate_router("mixed", router, dataset)
    assert result["by_category"]["clean_single"]["n"] == 2
    assert result["by_category"]["clean_single"]["hit_rate"] == 0.5
    assert result["by_category"]["clean_multi"]["n"] == 1
    assert result["by_category"]["clean_multi"]["hit_rate"] == 1.0
    print("test_category_breakdown_sums_correctly: PASS")


if __name__ == "__main__":
    test_perfect_router_scores_100_percent()
    test_always_wrong_router_scores_0_percent()
    test_partial_multi_label_hit_scores_correctly()
    test_single_label_router_cannot_exact_match_multi_label_truth()
    test_empty_prediction_scores_zero_precision_not_a_crash()
    test_category_breakdown_sums_correctly()
    print("\nAll eval harness tests passed.")
