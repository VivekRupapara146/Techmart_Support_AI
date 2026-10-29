# Router Comparison Report

Evaluated against 30 labeled queries (clean single-domain, genuinely multi-domain, harder/messier phrasing, and ambiguous cases).

## Overall Results

| Router | Exact Match | Hit Rate | Avg Precision | Avg Latency | Marginal Cost |
|---|---|---|---|---|---|
| v1 — Rule-based | 40.0% | 73.3% | 68.3% | 0.01 ms | none (local) |
| v2 — LLM-based (Gemini) | 50.0% | 86.7% | 78.3% | 477.71 ms | 1 LLM call / query |
| v2b — Trained classifier (Banking77) | 10.0% | 30.0% | 30.0% | 84.21 ms | none (local) |

## By Category

### ambiguous

| Router | Exact Match | Hit Rate |
|---|---|---|
| v1 — Rule-based | 0.0% | 100.0% |
| v2 — LLM-based (Gemini) | 0.0% | 100.0% |
| v2b — Trained classifier (Banking77) | 0.0% | 25.0% |

### clean_multi

| Router | Exact Match | Hit Rate |
|---|---|---|
| v1 — Rule-based | 40.0% | 100.0% |
| v2 — LLM-based (Gemini) | 60.0% | 100.0% |
| v2b — Trained classifier (Banking77) | 0.0% | 80.0% |

### clean_single

| Router | Exact Match | Hit Rate |
|---|---|---|
| v1 — Rule-based | 53.3% | 73.3% |
| v2 — LLM-based (Gemini) | 66.7% | 100.0% |
| v2b — Trained classifier (Banking77) | 20.0% | 20.0% |

### hard_paraphrase

| Router | Exact Match | Hit Rate |
|---|---|---|
| v1 — Rule-based | 33.3% | 33.3% |
| v2 — LLM-based (Gemini) | 33.3% | 33.3% |
| v2b — Trained classifier (Banking77) | 0.0% | 16.7% |

## Methodology Notes and Disclosed Limitations

- **v2b is structurally single-label**: Banking77 (its training data) is singly-labeled, so v2b can never exact-match a genuinely multi-domain query. Its exact-match score on `clean_multi`/`hard_paraphrase` cases will always undercount its real usefulness for those cases — `hit_rate` is the fairer metric for it.
- **v2b was trained on a different domain**: Banking77 is banking-domain data, mapped to this project's 5 retail-electronics categories as a proxy (see `ml/banking77_mapping.py`). Its strong 95.4% test accuracy on Banking77's own test set does not directly transfer to TechMart-style queries — this evaluation measures that real-world gap directly.
- **CFPB stress-testing, planned in Milestone 0, was not executed**: this sandbox's network blocks consumerfinance.gov, so the `hard_paraphrase` category (hand-written, deliberately messy phrasing) substitutes for it. This is a disclosed methodological limitation, not a hidden gap.
- **v1's misses are genuine keyword-coverage gaps**, not measurement bugs — e.g. "Wi-Fi" (hyphenated) and "firmware" aren't in the technical keyword list, and "furious"/"escalate" aren't in the complaint list. This is real evidence of rule-based routing's core weakness: brittleness to phrasing outside its fixed vocabulary.
- **Cost**: v1 and v2b run entirely locally (no API call, negligible marginal cost per query). v2 makes one live Gemini API call per routing decision — real dollar/quota cost scales with traffic, unlike v1/v2b.
- **Sample size**: 30 labeled queries is a small evaluation set. Results indicate real directional differences between routers but are not a large-scale statistical validation.