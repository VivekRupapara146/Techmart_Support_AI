"""
Response Aggregator, per the M0 decision doc.

Single agent -> pass through unchanged.
Multiple agents -> concatenate with a lightweight header per agent, no
extra LLM summarization call (avoids compounding hallucination risk and
extra token cost).
"""
from agents.base_agent import AgentResponse

AGENT_DISPLAY_NAMES = {
    "billing": "On billing",
    "technical": "On the technical issue",
    "product": "On the product",
    "complaint": "Regarding your complaint",
    "faq": "Here's what I found",
}


def aggregate(responses: list[AgentResponse]) -> str:
    if not responses:
        return "I wasn't able to find an agent to handle that — please rephrase your question."

    if len(responses) == 1:
        return responses[0].text

    parts = []
    for r in responses:
        header = AGENT_DISPLAY_NAMES.get(r.agent_name, r.agent_name.title())
        parts.append(f"**{header}:**\n{r.text}")
    return "\n\n".join(parts)


def aggregate_telemetry(responses: list[AgentResponse]) -> dict:
    """
    Real, measured numbers only — no estimates. When multiple agents handle
    one query (e.g. billing + technical), tokens/evidence are summed/merged
    and the grounded/degraded flags are conservative (grounded only if every
    agent that answered was grounded; degraded if any one of them degraded).
    """
    if not responses:
        return {
            "tokens_in": None, "tokens_out": None, "evidence": [],
            "agent_latencies_ms": {}, "retrieval_latency_ms": 0.0,
            "generation_latency_ms": 0.0, "grounded": False, "degraded": False,
            "top_similarity": 0.0,
        }

    tokens_in = [r.tokens_in for r in responses if r.tokens_in is not None]
    tokens_out = [r.tokens_out for r in responses if r.tokens_out is not None]

    return {
        "tokens_in": sum(tokens_in) if tokens_in else None,
        "tokens_out": sum(tokens_out) if tokens_out else None,
        "evidence": [chunk for r in responses for chunk in r.evidence],
        "agent_latencies_ms": {r.agent_name: round(r.latency_ms, 1) for r in responses},
        # Agents currently run sequentially (see run_chat_pipeline), so total
        # step time is the sum across however many agents handled this query.
        "retrieval_latency_ms": sum(r.retrieval_latency_ms for r in responses),
        "generation_latency_ms": sum(r.latency_ms for r in responses),
        "grounded": all(r.grounded for r in responses),
        "degraded": any(r.degraded for r in responses),
        "top_similarity": max(
            (c["similarity"] for r in responses for c in r.evidence), default=0.0
        ),
    }
