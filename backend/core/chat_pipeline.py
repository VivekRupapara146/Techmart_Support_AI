"""
Shared chat pipeline: route -> run agent(s) -> aggregate.

Used by BOTH the legacy unprefixed /chat endpoint (api/chat.py, kept
unchanged for backward compatibility with the original Milestone test
suite) and the versioned /v1/chat endpoint (api/v1_chat.py, the real
contract the React frontend speaks, with full telemetry). Keeping the
pipeline itself in one place means the two endpoints can never drift into
inconsistent routing/retrieval/aggregation behavior.
"""
import time
from dataclasses import dataclass, field

from core.config import settings
from core.logging import get_logger
from agents.base_agent import BaseAgent, AgentResponse
from agents.rag_agent import RAGAgent
from aggregator import aggregate, aggregate_telemetry
from router.rule_based import route as route_rule_based, AGENT_KEYWORDS
from router.llm_based import route as route_llm_based
from router.trained_classifier import route as route_trained_classifier
from router.types import RouteDecision
from prompts.support_prompts import AGENT_SYSTEM_PROMPTS
from llm.provider import GeminiLLMProvider
from rag.embeddings import GeminiEmbeddingProvider
from rag.ingestion import ingest_directory

logger = get_logger(__name__)

NO_SPECIALIST_REPLY = (
    "That request needs a specialist we haven't wired up yet in this build."
)

# Maps the frontend's display labels for the router switcher to the internal
# config keys the three router implementations are selected by. Anything
# unrecognized (or omitted) falls back to settings.active_router, so a typo
# in a request never silently 500s.
ROUTER_LABEL_MAP = {
    "TF-IDF + Logistic": "trained_classifier",
    "LLM Structured Output": "llm_based",
    "Rule-Based Regex": "rule_based",
    "rule_based": "rule_based",
    "llm_based": "llm_based",
    "trained_classifier": "trained_classifier",
}

# --- Agent registry (lazy singleton) ---------------------------------------
# Built on first use, not at import time, so a missing GEMINI_API_KEY only
# matters once a chat actually happens (app startup / /health / unit tests
# that never touch an agent all stay unaffected).
_registry: dict[str, BaseAgent] | None = None
_llm_provider = None


def get_llm_provider():
    global _llm_provider
    if _llm_provider is None:
        _llm_provider = GeminiLLMProvider()
    return _llm_provider


def get_agent_registry() -> dict[str, BaseAgent]:
    global _registry
    if _registry is None:
        llm = get_llm_provider()
        embedding_provider = GeminiEmbeddingProvider()
        store = ingest_directory("knowledge_base", embedding_provider, embedding_dim=3072)
        _registry = {
            name: RAGAgent(
                name=name,
                system_prompt=AGENT_SYSTEM_PROMPTS[name],
                llm=llm,
                embedding_provider=embedding_provider,
                store=store,
            )
            for name in AGENT_KEYWORDS.keys()
        }
    return _registry


def set_registry_for_tests(registry: dict[str, BaseAgent] | None) -> None:
    """Test-only hook: inject a registry built from fake providers instead of
    hitting real Gemini. Pass None to clear it back to the lazy-singleton
    behavior."""
    global _registry
    _registry = registry


def get_vector_store_count() -> int | None:
    """Real FAISS vector count for /health, or None if the registry hasn't
    been built yet (lazy singleton — a fresh process that hasn't served a
    chat request won't have embedded anything yet). All agents currently
    share one index (see agents/rag_agent.py's docstring), so any one of
    them is representative."""
    if _registry is None:
        return None
    first_agent = next(iter(_registry.values()), None)
    if first_agent is None:
        return None
    return first_agent._store.count()


def resolve_router_name(requested: str | None) -> str:
    if requested and requested in ROUTER_LABEL_MAP:
        return ROUTER_LABEL_MAP[requested]
    return settings.active_router


def get_route_decision(message: str, router_name: str) -> RouteDecision:
    if router_name == "llm_based":
        return route_llm_based(message, get_llm_provider())
    if router_name == "trained_classifier":
        return route_trained_classifier(message)
    return route_rule_based(message)


@dataclass
class ChatPipelineResult:
    reply_text: str
    routed_agents: list[str]
    router_name: str
    router_latency_ms: float
    unhandled: list[str]
    telemetry: dict = field(default_factory=dict)


def run_chat_pipeline(message: str, router_override: str | None = None) -> ChatPipelineResult:
    router_name = resolve_router_name(router_override)

    router_start = time.perf_counter()
    decision = get_route_decision(message, router_name)
    router_latency_ms = (time.perf_counter() - router_start) * 1000

    registry = get_agent_registry()
    responses: list[AgentResponse] = []
    unhandled: list[str] = []

    for agent_name in decision.agents:
        agent = registry.get(agent_name)
        if agent is None:
            unhandled.append(agent_name)
            continue
        responses.append(agent.respond(message))

    if unhandled:
        logger.info(f"Query routed to not-yet-implemented agents: {unhandled}")

    reply_text = aggregate(responses) if responses else NO_SPECIALIST_REPLY
    telemetry = aggregate_telemetry(responses)

    return ChatPipelineResult(
        reply_text=reply_text,
        routed_agents=decision.agents,
        router_name=router_name,
        router_latency_ms=router_latency_ms,
        unhandled=unhandled,
        telemetry=telemetry,
    )
