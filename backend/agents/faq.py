"""
FAQ Agent: the proof-of-concept agent for Milestone 3.

Enforces Instruction 17 (no ungrounded answers): if retrieval confidence
is below threshold, returns the honest fallback message instead of calling
the LLM to improvise.
"""
from agents.base_agent import BaseAgent, AgentResponse
from llm.provider import LLMProvider
from rag.embeddings import EmbeddingProvider
from rag.vector_store import VectorStore
from rag.retrieval import retrieve, CONFIDENCE_THRESHOLD
from prompts.support_prompts import FAQ_SYSTEM_PROMPT, INSUFFICIENT_CONTEXT_FALLBACK, build_rag_prompt


class FAQAgent(BaseAgent):
    name = "faq"

    def __init__(
        self,
        llm: LLMProvider,
        embedding_provider: EmbeddingProvider,
        store: VectorStore,
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
    ):
        self._llm = llm
        self._embedding_provider = embedding_provider
        self._store = store
        self._confidence_threshold = confidence_threshold

    def respond(self, query: str) -> AgentResponse:
        result = retrieve(
            query, self._embedding_provider, self._store, confidence_threshold=self._confidence_threshold
        )

        if result.insufficient_context:
            return AgentResponse(agent_name=self.name, text=INSUFFICIENT_CONTEXT_FALLBACK, grounded=False)

        prompt = build_rag_prompt(query, result.chunks)
        answer = self._llm.generate(prompt, system_prompt=FAQ_SYSTEM_PROMPT)
        return AgentResponse(agent_name=self.name, text=answer, grounded=True)
