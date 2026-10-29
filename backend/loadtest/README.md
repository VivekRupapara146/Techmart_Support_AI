# Load testing

`locustfile.py` drives the real `/v1` API (login → repeated chat messages
→ occasional health checks) with Locust. Results below are committed, real
numbers from runs in this repo — not estimates.

## Why these runs are against a locally mocked server

This project was built in a sandboxed environment with no outbound access
to Gemini's API (the same constraint documented in
`scripts/evaluate_router_v2.py` and `scripts/run_retrieval_evaluation.py`).
So these three runs use `scripts/run_dev_server_with_fakes.py` — the real
FastAPI app, real routing, real Pydantic validation, real Mongo
round-trips (mocked with mongomock-motor), real request/response
serialization — with only the LLM and embedding calls swapped for
deterministic, near-instant fakes.

**What this measures honestly**: the app's own overhead — routing,
retrieval bookkeeping, aggregation, telemetry, Mongo I/O, JSON
serialization.
**What it does NOT measure**: real Gemini latency, which dominates in
production. For that, the router comparison report
(`eval/router_comparison_report.md`) already has a real number from actual
Gemini calls: the LLM-based router alone averages **477.71 ms** per
routing decision. A real `/v1/chat` call adds that (routing) + a second
real Gemini call (generation) + real embedding calls (retrieval) on top of
the ~6-10ms of app overhead measured below — expect low-second-range
end-to-end latency against the real deployment, not the numbers here.

**To get the real, Gemini-backed number**: run this exact locustfile
against your actual deployed URL instead —
```bash
locust -f loadtest/locustfile.py --host https://your-backend-url \
    --users 10 --spawn-rate 2 --run-time 2m --headless \
    --csv loadtest/results/live
```
Keep `--users` and `--run-time` modest — this burns real Gemini quota.
Update the numbers below with that run once you have a live deployment.

## Run 1 — app overhead only, rate limiting relaxed

`RATE_LIMIT_DEFAULT=10000/minute`, 20 concurrent users, 60s
(`local_fake_raw_latency_stats.csv`):

| Endpoint | p50 | p90 | p95 | p99 | Max | Req/s |
|---|---|---|---|---|---|---|
| `POST /v1/chat` | 6 ms | 10 ms | 15 ms | 26 ms | 135 ms | 9.1 |
| `GET /v1/health` | 7 ms | 9 ms | 9 ms | 53 ms | 53 ms | 0.8 |
| `POST /v1/auth/login` | 14 ms | 21 ms | 26 ms | 26 ms | 26 ms | 0.3 |

536 `/v1/chat` requests, 264 failed — all 401s from users whose one-time
login (see Run 2) hit the auth rate limit during the ramp-up burst, not
from the chat endpoint itself (0 chat-specific errors once authenticated).

## Run 2 — default rate limits, 20 concurrent users from one IP

`RATE_LIMIT_DEFAULT=60/minute` (the shipped default), same load
(`local_fake_stats.csv`): most requests fail with `429 Too Many Requests`.

This is **the rate limiter working as designed**, not a performance
problem — `core/rate_limit.py` keys on remote address (`slowapi`'s
`get_remote_address`), and Locust's default `HttpUser` sends every
simulated user's traffic from the same source IP (the load-generator
machine). 20 simulated users sharing one IP's 60-requests/minute budget is
exactly the scenario the rate limit exists to catch — a single source
hammering the API — so seeing it trip here is the limiter doing its job,
confirmed under real concurrent load rather than just unit-tested
(`tests/test_milestone9.py` already covers the unit-level behavior; this
is the integration-level confirmation). A real multi-user production
deployment would see this budget per distinct client IP, not shared
across all users like a same-machine load test necessarily does.

## Run 3 — default rate limits, 5 concurrent users

(`local_fake_under_limit_stats.csv`): still trips 429s intermittently —
5 users each sending a request every 1-3s can collectively exceed 60/min
from one shared IP. Confirms the limit is tuned for roughly "one real
person's browser session," which is the right calibration for a resume
demo deployment (`core/config.py`'s `rate_limit_default`), not for
simulating many distinct users from a single test machine.

## Reproducing

```bash
cd backend
python -m scripts.run_dev_server_with_fakes &     # real app, fake LLM/embeddings/Mongo
RATE_LIMIT_DEFAULT=10000/minute python -m scripts.run_dev_server_with_fakes &  # for Run 1 specifically
locust -f loadtest/locustfile.py --host http://localhost:8000 \
    --users 20 --spawn-rate 5 --run-time 60s --headless \
    --csv loadtest/results/my_run
```
