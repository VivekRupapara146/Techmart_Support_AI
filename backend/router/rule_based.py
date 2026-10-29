"""
Router v1: rule/keyword-based. Multi-agent match is expected and allowed
(e.g. "paid yesterday but Premium still locked" -> billing + technical).
Zero matches route to FAQ as a safe default (never silently drops a query).

matched_keywords is logged so we have real data before comparing this
against v2 (LLM-based) and v2b (trained classifier) later.
"""
import re

from router.types import RouteDecision, DEFAULT_AGENT
from core.logging import get_logger

logger = get_logger(__name__)

# Keyword sets per agent. Deliberately simple/editable — this is the part
# most likely to need tuning once real query logs exist.
AGENT_KEYWORDS: dict[str, list[str]] = {
    "billing": ["invoice", "refund", "charged", "payment", "paid", "billing", "subscription fee", "credit card", "premium"],
    "technical": ["error", "login", "install", "bug", "crash", "not working", "locked", "password"],
    "product": ["specs", "specification", "warranty", "compatible", "compatibility", "features", "model"],
    "complaint": ["complaint", "unhappy", "disappointed", "terrible", "worst", "angry", "frustrated"],
    "faq": ["hours", "shipping", "policy", "how do i", "where is"],
}


def _normalize(query: str) -> str:
    return re.sub(r"[^\w\s]", "", query.lower()).strip()


def route(query: str) -> RouteDecision:
    normalized = _normalize(query)

    matched: dict[str, list[str]] = {}
    for agent, keywords in AGENT_KEYWORDS.items():
        hits = [kw for kw in keywords if kw in normalized]
        if hits:
            matched[agent] = hits

    agents = list(matched.keys()) if matched else [DEFAULT_AGENT]

    decision = RouteDecision(agents=agents, confidence="rule_based", matched_keywords=matched)

    logger.info(
        "route_decision_logged",
        # Length only, never the raw text: user queries may contain PII.
        extra={"query_length": len(query), "agents": agents, "matched_keywords": matched},
    )

    return decision
