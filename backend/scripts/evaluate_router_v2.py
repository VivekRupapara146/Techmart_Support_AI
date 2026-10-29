"""
Evaluates Router v2 (LLM-based, Gemini structured output) against the
same labeled dataset used for v1 and v2b — run this locally where your
Gemini key works (this can't run in the sandbox, since Gemini's API
domain is network-blocked there).

Run from backend/: python -m scripts.evaluate_router_v2
Produces: eval/results_v2.json (same format as v1/v2b, so it merges
cleanly with eval.generate_report)

Note on cost: this makes one real Gemini API call per query (30 calls
total). At Gemini 3.1 Flash Lite's free tier (15 RPM), this comfortably
fits in one run without hitting rate limits.
"""
import sys
sys.path.insert(0, ".")

from llm.provider import GeminiLLMProvider
from router.llm_based import route as route_v2
from eval.harness import evaluate_router, save_results, print_summary


def main():
    llm = GeminiLLMProvider()
    results = evaluate_router("v2_llm_based", lambda q: route_v2(q, llm).agents)
    print_summary(results)
    save_results(results, "eval/results_v2.json")
    print("\nSaved to eval/results_v2.json — paste this file's content back, "
          "or run `python -m eval.generate_report` locally if you have all 3 "
          "results_*.json files present.")


if __name__ == "__main__":
    main()
