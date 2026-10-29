# TechMart Support — Backend

FastAPI backend for a multi-agent RAG customer support system. See the
repo root's `README.md` for the project overview and `DEPLOYMENT.md` for
hosting this on AWS App Runner (primary) or Render (fallback).

## Setup

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then fill in real values
```

Required in `.env`: `JWT_SECRET_KEY`, `MONGO_URI`, `GEMINI_API_KEY`.
Everything else has a sensible default — see `.env.example` for the full
list and comments.

## Run

```bash
uvicorn main:app --reload
```

Visit `http://127.0.0.1:8000/docs` for interactive OpenAPI docs.

No Gemini key / Mongo yet, but want to poke at the API? —
`python -m scripts.run_dev_server_with_fakes` runs the real app with a
mocked Mongo and a fake LLM/embedding-backed agent registry. Not for
anything resembling production (see that script's docstring), but useful
for frontend development or load testing without burning real API quota.

## API

Two generations of the same endpoints are mounted side by side:

- **`/v1/*`** — the real, versioned contract (`api/v1_*.py`), camelCase
  JSON, real telemetry (tokens/cost/latency/evidence). This is what the
  React frontend speaks.
- **Unprefixed** (`/chat`, `/auth/login`, `/health`) — kept for backward
  compatibility with the original Milestone test suite. Both share the
  same underlying pipeline (`core/chat_pipeline.py`) so they can't drift
  apart in behavior, only in response shape.

| Endpoint | What it does |
|---|---|
| `POST /v1/auth/login` | Demo-account JWT login |
| `POST /v1/chat` | Routes to 1+ specialist agent(s), returns a grounded reply + real evidence/telemetry |
| `GET /v1/health` | Real FastAPI/Mongo/FAISS status |
| `GET /v1/evaluation/summary` | Real router-comparison + retrieval metrics, from committed eval runs |

## Test

```bash
pip install -r requirements-dev.txt   # mongomock-motor, locust
for f in tests/test_*.py; do python "$f"; done
```

Same loop CI runs (`.github/workflows/ci.yml`): 15 files, 92 checks, all
self-contained scripts (no pytest required) — each prints PASS/FAIL per
case and exits non-zero on failure. No real Mongo or Gemini call is ever
made in tests — every agent/router test injects a fake LLM/embedding
provider (`tests/fake_*.py`, `tests/scripted_llm.py`), and Mongo is mocked
with `mongomock-motor`.

## Evaluation

```bash
python -m eval.run_local_evaluation        # router comparison (v1, v2b — fully offline)
python -m scripts.evaluate_router_v2       # router comparison (v2 — needs real GEMINI_API_KEY)
python -m scripts.run_retrieval_evaluation # retrieval hit@k/MRR/groundedness — needs real GEMINI_API_KEY
```
Results are committed JSON (`eval/results_*.json`, `eval/retrieval_results.json`)
served by `GET /v1/evaluation/summary` — not recomputed per-request. See
`eval/router_comparison_report.md` for the router write-up and
`eval/retrieval_eval.py`'s docstring for exactly what the retrieval
metrics mean and don't claim to measure (no LLM-hallucination judge; a
stricter, honest proxy instead — see that docstring).

## Load testing

```bash
python -m scripts.run_dev_server_with_fakes &
locust -f loadtest/locustfile.py --host http://localhost:8000 \
    --users 20 --spawn-rate 5 --run-time 60s --headless --csv loadtest/results/my_run
```
See `loadtest/README.md` for committed, real p50/p95/p99 numbers and why
they're measured against a fake-LLM-backed server (and how to re-run
against a live deployment for the real, Gemini-inclusive number).

## Train Router v2b (optional — a trained artifact ships already)

```bash
python -m ml.train_router_v2b
```

Re-downloads aren't automatic — `banking77_train.csv` / `banking77_test.csv`
must be present in `backend/` (gitignored; see repo root for the source).

## Project layout

```
backend/
├── main.py                 # app entrypoint — mounts both API generations
├── core/
│   ├── chat_pipeline.py    # shared routing -> agents -> aggregation logic
│   ├── request_context.py  # per-request correlation ID
│   ├── config.py           # all env vars, validated via Pydantic Settings
│   ├── logging.py          # structured JSON logs
│   └── rate_limit.py       # per-IP rate limiting
├── auth/                   # JWT + demo credential login (service.py: shared check)
├── database/                # MongoDB connection + conversation storage
├── models/                  # Pydantic schemas
├── rag/                     # chunking, embeddings, FAISS store, retrieval
├── router/                  # 3 router implementations (rule-based/LLM/trained)
├── agents/                  # generic RAG agent + base interface
├── prompts/                 # system prompts, incl. prompt-injection mitigation
├── llm/                     # Gemini provider: retry/backoff/timeout/degrade
├── ml/                      # Router v2b training + Banking77 mapping
├── api/                     # /v1/* (versioned) + legacy unprefixed routes
├── eval/                    # router comparison + retrieval hit@k/MRR harnesses
├── loadtest/                # Locust load test + committed results
├── scripts/                 # ops helpers (password hash, eval runners, fake dev server)
└── tests/                   # test suite (92 checks across 15 files)
```
