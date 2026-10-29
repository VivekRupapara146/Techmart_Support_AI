"""
Versioned chat endpoint — the contract the React frontend speaks
(frontend/src/services/apiClient.ts: sendChat()). Wraps
core/chat_pipeline.py (shared with the legacy /chat endpoint) and reports
real, measured telemetry: actual FAISS similarity scores as evidence, actual
Gemini token usage and a cost estimate derived from it, actual per-step
latency, and a real running cost per session (summed from stored message
history, not a per-request-only number).

What's intentionally NOT here, per the agreed scope: a fabricated
hallucination-detector score, ticket/SLA escalation workflow, and anything
resembling a multi-tenant enterprise cluster. The frontend's own mock data
for those stays unused once this endpoint responds — see README.
"""
import time
import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from auth.jwt_handler import get_current_subject
from core.config import settings
from core.rate_limit import limiter
from core.request_context import get_request_id
from core.chat_pipeline import run_chat_pipeline
from database.mongo import get_db
from database.conversations import append_message, get_history
from models.conversation import Message

router = APIRouter(prefix="/chat", tags=["chat (v1)"])

SESSION_ID_PATTERN = r"^[a-zA-Z0-9\-]{1,64}$"


class ChatRequestV1(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    # The frontend sends `query`; the legacy endpoint's field is `message` —
    # accept either so both API generations work off one request model.
    message: str = Field(
        min_length=1, max_length=2000,
        validation_alias=AliasChoices("message", "query"),
    )
    session_id: str | None = Field(
        default=None, pattern=SESSION_ID_PATTERN,
        validation_alias=AliasChoices("session_id", "sessionId"),
    )
    # Optional per-request router override (the frontend's router switcher).
    # Unrecognized/omitted values fall back to ACTIVE_ROUTER — see
    # core/chat_pipeline.ROUTER_LABEL_MAP.
    router_override: str | None = Field(
        default=None, validation_alias=AliasChoices("router", "router_override"),
    )


class EvidenceChunkOut(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: str
    section: str
    similarity: float
    snippet: str


class PipelineStepOut(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    step: int
    title: str
    latency_ms: float
    description: str
    status: str  # "complete" | "warning"


class TelemetryOut(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    trace_id: str
    e2e_latency_ms: float
    tokens_in: int | None
    tokens_out: int | None
    total_tokens: int | None
    step_cost_usd: float | None
    cumulative_cost_usd: float | None
    router_used: str
    specialist_agent: str
    grounded_score: float  # 0-100, derived from real top retrieval similarity
    grounded: bool
    degraded: bool
    steps: list[PipelineStepOut]


class ChatReplyOut(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    id: str
    role: str = "assistant"
    content: str
    specialist: str
    grounded_score: float
    evidence: list[EvidenceChunkOut]
    session_id: str


class ChatResponseV1(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    reply: ChatReplyOut
    telemetry: TelemetryOut
    routed_agents: list[str]


def _estimate_cost_usd(tokens_in: int | None, tokens_out: int | None) -> float | None:
    """Real arithmetic on real token counts, using the configurable pricing
    in core/config.py — None (not 0) when we have no token counts at all, so
    the frontend can tell "zero cost" apart from "unknown"."""
    if tokens_in is None and tokens_out is None:
        return None
    cost = 0.0
    if tokens_in:
        cost += (tokens_in / 1000) * settings.gemini_input_price_per_1k_usd
    if tokens_out:
        cost += (tokens_out / 1000) * settings.gemini_output_price_per_1k_usd
    return round(cost, 6)


@router.post("", response_model=ChatResponseV1)
@limiter.limit(settings.rate_limit_default)
async def chat_v1(request: Request, payload: ChatRequestV1, subject: str = Depends(get_current_subject)):
    session_id = payload.session_id or str(uuid.uuid4())
    db = get_db()

    pipeline_start = time.perf_counter()
    result = run_chat_pipeline(payload.message, router_override=payload.router_override)
    e2e_latency_ms = (time.perf_counter() - pipeline_start) * 1000

    telemetry = result.telemetry
    tokens_in = telemetry.get("tokens_in")
    tokens_out = telemetry.get("tokens_out")
    total_tokens = (
        (tokens_in or 0) + (tokens_out or 0)
        if (tokens_in is not None or tokens_out is not None) else None
    )
    step_cost = _estimate_cost_usd(tokens_in, tokens_out)
    grounded_score = round(telemetry.get("top_similarity", 0.0) * 100, 1)
    specialist = ", ".join(result.routed_agents) if result.routed_agents else "faq"

    # Real running cost for this session: prior assistant messages' stored
    # cost_usd, plus this turn's — not reset to zero every request.
    prior_messages = await get_history(db, session_id, subject) or []
    prior_cost = sum(m.cost_usd or 0.0 for m in prior_messages if m.role == "assistant")
    cumulative_cost = (
        round(prior_cost + (step_cost or 0.0), 6) if (step_cost is not None or prior_cost)
        else None
    )

    await append_message(db, session_id, subject, Message(role="user", content=payload.message))
    await append_message(
        db, session_id, subject,
        Message(
            role="assistant", content=result.reply_text, routed_agents=result.routed_agents,
            tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=step_cost,
        ),
    )

    evidence_out = [
        EvidenceChunkOut(
            id=f"{c['source']}#{c.get('chunk_index', 0)}",
            section=c["source"],
            similarity=round(c["similarity"] * 100, 1),
            snippet=c["snippet"],
        )
        for c in telemetry.get("evidence", [])
    ]

    steps = [
        PipelineStepOut(
            step=1, title="Query received", latency_ms=0.0,
            description=f"{len(payload.message)} chars, validated.", status="complete",
        ),
        PipelineStepOut(
            step=2, title="Router classification", latency_ms=round(result.router_latency_ms, 2),
            description=f"{result.router_name}: routed to {', '.join(result.routed_agents) or 'none'}.",
            status="complete",
        ),
        PipelineStepOut(
            step=3, title="Knowledge retrieval", latency_ms=round(telemetry.get("retrieval_latency_ms", 0.0), 2),
            description=f"FAISS: top similarity {grounded_score:.1f}%.",
            status="complete" if telemetry.get("grounded") else "warning",
        ),
        PipelineStepOut(
            step=4, title="Answer generation", latency_ms=round(telemetry.get("generation_latency_ms", 0.0), 2),
            description=(
                "Model provider unreachable after retries — fallback used."
                if telemetry.get("degraded") else "Generated from retrieved context."
            ),
            status="warning" if telemetry.get("degraded") else "complete",
        ),
    ]

    reply = ChatReplyOut(
        id=f"msg-{uuid.uuid4().hex[:12]}",
        content=result.reply_text,
        specialist=specialist,
        grounded_score=grounded_score,
        evidence=evidence_out,
        session_id=session_id,
    )
    telemetry_out = TelemetryOut(
        trace_id=get_request_id(),
        e2e_latency_ms=round(e2e_latency_ms, 2),
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        total_tokens=total_tokens,
        step_cost_usd=step_cost,
        cumulative_cost_usd=cumulative_cost,
        router_used=result.router_name,
        specialist_agent=specialist,
        grounded_score=grounded_score,
        grounded=telemetry.get("grounded", False),
        degraded=telemetry.get("degraded", False),
        steps=steps,
    )

    return ChatResponseV1(reply=reply, telemetry=telemetry_out, routed_agents=result.routed_agents)
