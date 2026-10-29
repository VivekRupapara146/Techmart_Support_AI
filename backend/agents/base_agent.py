"""
Shared agent interface. Every specialized agent (FAQ, Billing, Technical,
Product, Complaint) implements this so the aggregator can treat them
uniformly (Instruction 16 — isolated, not tightly coupled).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class AgentResponse:
    agent_name: str
    text: str
    grounded: bool  # False when the confidence-threshold fallback fired, or the LLM call degraded
    evidence: list[dict] = field(default_factory=list)  # real retrieved chunks: source/similarity/snippet
    tokens_in: int | None = None
    tokens_out: int | None = None
    retrieval_latency_ms: float = 0.0  # time spent embedding the query + FAISS search
    latency_ms: float = 0.0  # time spent in the LLM generation call
    degraded: bool = False  # True when the LLM call exhausted retries and returned the fallback apology


class BaseAgent(ABC):
    name: str

    @abstractmethod
    def respond(self, query: str) -> AgentResponse:
        raise NotImplementedError
