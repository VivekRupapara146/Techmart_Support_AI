"""
Shared router decision type. Every router implementation (rule-based,
LLM-based, trained-classifier) returns this same shape, so the chat
endpoint and comparison harness (Milestone 10) can treat them uniformly.
"""
from dataclasses import dataclass, field

VALID_AGENTS = ["billing", "technical", "product", "complaint", "faq"]
DEFAULT_AGENT = "faq"


@dataclass
class RouteDecision:
    agents: list[str]
    confidence: str  # "rule_based" | "llm_based" | "trained_classifier"
    matched_keywords: dict[str, list[str]] = field(default_factory=dict)
