"""
Regression test for the retrieval confidence threshold calibration
(Milestone 10 follow-up).

Encodes the REAL Gemini embedding scores captured when calibrating
CONFIDENCE_THRESHOLD (see rag/retrieval.py and scripts/calibrate_threshold.py).
This can't re-run the real embedding call (no live Gemini access in CI/
offline environments), but it locks in the specific bug we found and
fixed: the old placeholder threshold (0.55) would have wrongly rejected
a genuinely answerable query ("how do I reset my password", real score
0.5325) as insufficient context. If CONFIDENCE_THRESHOLD is ever raised
above that real score again without re-running calibration, this test
catches it.
"""
import sys
sys.path.insert(0, ".")

from rag.retrieval import CONFIDENCE_THRESHOLD

# Real scores captured 2026-07-18 via scripts/calibrate_threshold.py
# against actual Gemini embeddings and the real 6-doc knowledge base.
REAL_ON_TOPIC_SCORES = {
    "how do I get a refund for my order": 0.6505,
    "why is my Premium subscription still locked after payment": 0.7486,
    "what does the product warranty cover": 0.7104,
    "how do I escalate a complaint": 0.7564,
    "my device won't connect to wifi": 0.6627,
    "what are your store hours": 0.6202,
    "how long does shipping take": 0.5860,
    "how do I reset my password": 0.5325,  # the one that exposed the bug
}

REAL_OFF_TOPIC_SCORES = {
    "what's the weather like today": 0.4553,
    "who won the world cup": 0.4520,
    "can you write me a poem": 0.4913,  # highest off-topic score
    "what is the capital of France": 0.4374,
    "tell me a joke": 0.4875,
}


def test_threshold_does_not_reject_the_known_true_positive():
    """The specific bug: 0.55 would have rejected this genuinely
    answerable query. The current threshold must not repeat that."""
    weakest_true_positive_score = min(REAL_ON_TOPIC_SCORES.values())
    assert CONFIDENCE_THRESHOLD < weakest_true_positive_score, (
        f"CONFIDENCE_THRESHOLD ({CONFIDENCE_THRESHOLD}) is >= the real score of a "
        f"genuinely answerable query ({weakest_true_positive_score}). This would "
        f"wrongly trigger the 'insufficient context' fallback for a real, "
        f"answerable question. Re-run scripts/calibrate_threshold.py before "
        f"changing this value."
    )
    print(f"test_threshold_does_not_reject_the_known_true_positive: PASS "
          f"(threshold={CONFIDENCE_THRESHOLD} < {weakest_true_positive_score})")


def test_threshold_still_rejects_the_known_true_negatives():
    """The current threshold must still reject all real off-topic queries."""
    strongest_true_negative_score = max(REAL_OFF_TOPIC_SCORES.values())
    assert CONFIDENCE_THRESHOLD > strongest_true_negative_score, (
        f"CONFIDENCE_THRESHOLD ({CONFIDENCE_THRESHOLD}) is <= the real score of a "
        f"genuinely off-topic query ({strongest_true_negative_score}). This would "
        f"let an off-topic query slip through as if it were grounded."
    )
    print(f"test_threshold_still_rejects_the_known_true_negatives: PASS "
          f"(threshold={CONFIDENCE_THRESHOLD} > {strongest_true_negative_score})")


if __name__ == "__main__":
    test_threshold_does_not_reject_the_known_true_positive()
    test_threshold_still_rejects_the_known_true_negatives()
    print("\nAll threshold calibration regression tests passed.")
