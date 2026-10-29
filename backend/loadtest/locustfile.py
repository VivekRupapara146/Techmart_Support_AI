"""
Locust load test for the versioned /v1 API.

Each simulated user logs in once (on_start), then repeatedly sends chat
messages drawn from a realistic query pool (the same style of query as
eval/dataset.py / eval/retrieval_dataset.py — not synthetic "test test
test" filler), occasionally checking /v1/health too.

Run against a locally mocked server (see README.md in this directory for
why that's a legitimate, separately-reported number):
    python -m scripts.run_dev_server_with_fakes &
    locust -f loadtest/locustfile.py --host http://localhost:8000 \
        --users 20 --spawn-rate 5 --run-time 2m --headless \
        --csv loadtest/results/local_fake

Or against a real deployment (Gemini-backed, the number that matters):
    locust -f loadtest/locustfile.py --host https://your-backend-url \
        --users 10 --spawn-rate 2 --run-time 2m --headless \
        --csv loadtest/results/live
Real Gemini calls cost quota — keep --users and --run-time modest.
"""
import random

from locust import HttpUser, task, between

QUERIES = [
    "I was charged twice for the same order",
    "How do I get a refund for a defective item",
    "My device won't connect to Wi-Fi",
    "The app keeps showing a login error",
    "What is the warranty period on this product",
    "I want to file a complaint about my experience",
    "What are your store hours",
    "How long does shipping take",
    "I paid yesterday but Premium is still locked with a login error",
    "How do I reset my password",
    "Can I switch from monthly to annual billing mid-cycle?",
    "My order is late and I'm not happy about it",
]


class SupportChatUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        response = self.client.post(
            "/v1/auth/login",
            json={"username": f"loadtest-user-{random.randint(1, 10_000)}", "password": "whatever"},
            name="/v1/auth/login",
        )
        self.token = response.json().get("accessToken", "") if response.ok else ""
        self.session_id = f"loadtest-{random.randint(1, 10**9)}"

    @task(10)
    def send_chat_message(self):
        self.client.post(
            "/v1/chat",
            json={"query": random.choice(QUERIES), "sessionId": self.session_id},
            headers={"Authorization": f"Bearer {self.token}"},
            name="/v1/chat",
        )

    @task(1)
    def check_health(self):
        self.client.get("/v1/health", name="/v1/health")
