"""
Runs the evaluation harness for the two routers that work fully offline:
- v1 (rule-based): no dependencies at all
- v2b (trained classifier): needs the trained artifact (artifacts/router_v2b/model.joblib)

v2 (LLM-based) requires a live Gemini call and is evaluated separately by
scripts/evaluate_router_v2.py (run locally where a Gemini key works).

Run: python -m eval.run_local_evaluation
"""
from router.rule_based import route as route_v1
from router.trained_classifier import route as route_v2b
from eval.harness import evaluate_router, save_results, print_summary


def main():
    v1_results = evaluate_router("v1_rule_based", lambda q: route_v1(q).agents)
    print_summary(v1_results)
    save_results(v1_results, "eval/results_v1.json")

    v2b_results = evaluate_router("v2b_trained_classifier", lambda q: route_v2b(q).agents)
    print_summary(v2b_results)
    save_results(v2b_results, "eval/results_v2b.json")

    print("\nResults saved to eval/results_v1.json and eval/results_v2b.json")
    print("Now run scripts/evaluate_router_v2.py locally (needs a live Gemini key) "
          "to produce eval/results_v2.json, then run eval.generate_report to merge all three.")


if __name__ == "__main__":
    main()
