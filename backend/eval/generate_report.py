"""
Merges eval/results_v1.json, results_v2.json, results_v2b.json (whichever
are present) into a single markdown comparison report for the capstone
write-up.

Run: python -m eval.generate_report
"""
import json
import os

RESULT_FILES = {
    "v1_rule_based": "eval/results_v1.json",
    "v2_llm_based": "eval/results_v2.json",
    "v2b_trained_classifier": "eval/results_v2b.json",
}

DISPLAY_NAMES = {
    "v1_rule_based": "v1 — Rule-based",
    "v2_llm_based": "v2 — LLM-based (Gemini)",
    "v2b_trained_classifier": "v2b — Trained classifier (Banking77)",
}


# Qualitative on purpose: per-query token usage is not recorded yet, so a
# dollar figure here would be invented. Replace with measured cost once
# token tracking lands.
ROUTER_COST = {
    "v1_rule_based": "none (local)",
    "v2_llm_based": "1 LLM call / query",
    "v2b_trained_classifier": "none (local)",
}


def load_available_results() -> dict:
    loaded = {}
    for key, path in RESULT_FILES.items():
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                loaded[key] = json.load(f)
    return loaded


def generate_markdown(results: dict) -> str:
    lines = ["# Router Comparison Report", ""]
    lines.append(f"Evaluated against {next(iter(results.values()))['n_cases']} labeled queries "
                  f"(clean single-domain, genuinely multi-domain, harder/messier phrasing, and "
                  f"ambiguous cases).")
    lines.append("")

    lines.append("## Overall Results")
    lines.append("")
    lines.append("| Router | Exact Match | Hit Rate | Avg Precision | Avg Latency | Marginal Cost |")
    lines.append("|---|---|---|---|---|---|")
    for key, data in results.items():
        o = data["overall"]
        lines.append(
            f"| {DISPLAY_NAMES[key]} | {o['exact_match_rate']:.1%} | {o['hit_rate']:.1%} | "
            f"{o['avg_precision']:.1%} | {o['avg_latency_ms']:.2f} ms | {ROUTER_COST[key]} |"
        )
    lines.append("")

    lines.append("## By Category")
    lines.append("")
    all_categories = sorted(set(
        cat for data in results.values() for cat in data["by_category"].keys()
    ))
    for cat in all_categories:
        lines.append(f"### {cat}")
        lines.append("")
        lines.append("| Router | Exact Match | Hit Rate |")
        lines.append("|---|---|---|")
        for key, data in results.items():
            stats = data["by_category"].get(cat)
            if stats:
                lines.append(f"| {DISPLAY_NAMES[key]} | {stats['exact_match_rate']:.1%} | {stats['hit_rate']:.1%} |")
        lines.append("")

    lines.append("## Methodology Notes and Disclosed Limitations")
    lines.append("")
    lines.append(
        "- **v2b is structurally single-label**: Banking77 (its training data) is singly-labeled, "
        "so v2b can never exact-match a genuinely multi-domain query. Its exact-match score on "
        "`clean_multi`/`hard_paraphrase` cases will always undercount its real usefulness for "
        "those cases — `hit_rate` is the fairer metric for it."
    )
    lines.append(
        "- **v2b was trained on a different domain**: Banking77 is banking-domain data, mapped "
        "to this project's 5 retail-electronics categories as a proxy (see "
        "`ml/banking77_mapping.py`). Its strong 95.4% test accuracy on Banking77's own test set "
        "does not directly transfer to TechMart-style queries — this evaluation measures that "
        "real-world gap directly."
    )
    lines.append(
        "- **CFPB stress-testing, planned in Milestone 0, was not executed**: this sandbox's "
        "network blocks consumerfinance.gov, so the `hard_paraphrase` category (hand-written, "
        "deliberately messy phrasing) substitutes for it. This is a disclosed methodological "
        "limitation, not a hidden gap."
    )
    lines.append(
        "- **v1's misses are genuine keyword-coverage gaps**, not measurement bugs — e.g. "
        "\"Wi-Fi\" (hyphenated) and \"firmware\" aren't in the technical keyword list, and "
        "\"furious\"/\"escalate\" aren't in the complaint list. This is real evidence of "
        "rule-based routing's core weakness: brittleness to phrasing outside its fixed vocabulary."
    )
    lines.append(
        "- **Cost**: v1 and v2b run entirely locally (no API call, negligible marginal cost per "
        "query). v2 makes one live Gemini API call per routing decision — real dollar/quota cost "
        "scales with traffic, unlike v1/v2b."
    )
    lines.append(
        "- **Sample size**: 30 labeled queries is a small evaluation set. Results indicate real "
        "directional differences between routers but are not a large-scale statistical validation."
    )

    return "\n".join(lines)


def main():
    results = load_available_results()
    if not results:
        print("No results_*.json files found in eval/. Run eval.run_local_evaluation "
              "and scripts.evaluate_router_v2 first.")
        return

    missing = set(RESULT_FILES.keys()) - set(results.keys())
    if missing:
        print(f"Note: generating a partial report — missing results for: {sorted(missing)}")

    report = generate_markdown(results)
    with open("eval/router_comparison_report.md", "w", encoding="utf-8") as f:
        f.write(report)
    print("Report written to eval/router_comparison_report.md")
    print("\n" + report)


if __name__ == "__main__":
    main()
