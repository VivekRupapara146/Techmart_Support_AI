"""
Router v2: LLM-based intent classification via Gemini structured output.

Defensive design (Instruction 9 — don't suppress errors, but don't let a
malformed/unexpected LLM response take down routing either): if the model
returns invalid JSON, an empty result, or an unrecognized agent name, we
log the failure and fall back to Router v1 (rule-based) rather than
crashing the request. This also means v2 can never route to a
nonexistent agent — invalid names are dropped, not passed through.
"""
import json

from llm.provider import LLMProvider
from router.types import RouteDecision, VALID_AGENTS, DEFAULT_AGENT
from router import rule_based
from core.logging import get_logger

logger = get_logger(__name__)

CLASSIFIER_SYSTEM_PROMPT = f"""You are an intent classifier for a customer support system.
Classify the user's message into one or more of these categories: {', '.join(VALID_AGENTS)}.
A message can match multiple categories if it genuinely spans more than one topic
(e.g. a billing issue that is also a technical problem).
Respond with ONLY a JSON object in this exact shape, no other text:
{{"agents": ["category1", "category2"]}}
If no category clearly applies, respond with {{"agents": ["faq"]}}."""


def route(query: str, llm: LLMProvider) -> RouteDecision:
    try:
        raw = llm.generate(query, system_prompt=CLASSIFIER_SYSTEM_PROMPT)
        parsed = _parse_response(raw)

        if parsed is None:
            logger.warning(f"LLM router returned unparseable response, falling back to v1: {raw!r}")
            return _fallback(query)

        return RouteDecision(agents=parsed, confidence="llm_based")

    except Exception as exc:
        logger.error(f"LLM router call failed, falling back to v1: {exc}")
        return _fallback(query)


def _parse_response(raw: str) -> list[str] | None:
    cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None

    agents = data.get("agents")
    if not isinstance(agents, list) or not agents:
        return None

    valid = [a for a in agents if a in VALID_AGENTS]
    if not valid:
        return None

    return valid


def _fallback(query: str) -> RouteDecision:
    fallback_decision = rule_based.route(query)
    return RouteDecision(
        agents=fallback_decision.agents,
        confidence="llm_based_fallback_to_rule_based",
        matched_keywords=fallback_decision.matched_keywords,
    )
