"""
Evaluation harness for router comparison (Milestone 10).

Metrics, chosen to be fair across routers with different capabilities:
- exact_match: predicted agent set == expected agent set. Strict; note
  that v2b (single-label by construction, since Banking77 is singly-
  labeled) can NEVER exact-match a multi-label expected case — this is
  a structural, disclosed limitation, not a bug.
- hit_rate: at least one predicted agent is in the expected set. Fair
  across all routers regardless of multi-label capability.
- precision: fraction of predicted agents that are actually expected
  (only meaningful for multi-label predictors; always 0 or 1 for v2b).

Results are broken down by category (clean_single / clean_multi /
hard_paraphrase / ambiguous) so we can see where routers actually differ,
not just an aggregate number that hides the interesting cases.
"""
import time
import json
from dataclasses import dataclass, asdict

from eval.dataset import EVAL_DATASET, EvalCase


@dataclass
class CaseResult:
    query: str
    category: str
    expected: list[str]
    predicted: list[str]
    exact_match: bool
    hit: bool
    precision: float
    latency_ms: float


def evaluate_router(router_name: str, route_fn, dataset: list[EvalCase] = EVAL_DATASET) -> dict:
    """
    route_fn: callable(query: str) -> list[str] of predicted agent names.
    Timing is measured per-call around route_fn only.
    """
    results: list[CaseResult] = []

    for case in dataset:
        start = time.perf_counter()
        predicted = route_fn(case.query)
        elapsed_ms = (time.perf_counter() - start) * 1000

        expected_set = set(case.expected_agents)
        predicted_set = set(predicted)

        exact_match = predicted_set == expected_set
        hit = len(predicted_set & expected_set) > 0
        precision = (len(predicted_set & expected_set) / len(predicted_set)) if predicted_set else 0.0

        results.append(CaseResult(
            query=case.query, category=case.category, expected=case.expected_agents,
            predicted=predicted, exact_match=exact_match, hit=hit, precision=precision,
            latency_ms=elapsed_ms,
        ))

    return summarize(router_name, results)


def summarize(router_name: str, results: list[CaseResult]) -> dict:
    n = len(results)
    overall = {
        "exact_match_rate": sum(r.exact_match for r in results) / n,
        "hit_rate": sum(r.hit for r in results) / n,
        "avg_precision": sum(r.precision for r in results) / n,
        "avg_latency_ms": sum(r.latency_ms for r in results) / n,
    }

    by_category = {}
    categories = sorted(set(r.category for r in results))
    for cat in categories:
        cat_results = [r for r in results if r.category == cat]
        cn = len(cat_results)
        by_category[cat] = {
            "n": cn,
            "exact_match_rate": sum(r.exact_match for r in cat_results) / cn,
            "hit_rate": sum(r.hit for r in cat_results) / cn,
        }

    return {
        "router": router_name,
        "n_cases": n,
        "overall": overall,
        "by_category": by_category,
        "cases": [asdict(r) for r in results],
    }


def save_results(results: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)


def print_summary(results: dict) -> None:
    print(f"\n=== {results['router']} ({results['n_cases']} cases) ===")
    o = results["overall"]
    print(f"  Exact match rate: {o['exact_match_rate']:.1%}")
    print(f"  Hit rate:         {o['hit_rate']:.1%}")
    print(f"  Avg precision:    {o['avg_precision']:.1%}")
    print(f"  Avg latency:      {o['avg_latency_ms']:.2f} ms")
    print("  By category:")
    for cat, stats in results["by_category"].items():
        print(f"    {cat:16s} (n={stats['n']:2d}): exact={stats['exact_match_rate']:.1%}  hit={stats['hit_rate']:.1%}")
