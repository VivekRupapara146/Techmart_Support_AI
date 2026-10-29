"""
Deterministic fake LLM provider for tests. Echoes back a recognizable
string derived from the prompt so tests can assert on it without needing
a real Gemini call.

NOT for production use.
"""
from llm.provider import LLMProvider


class FakeLLMProvider(LLMProvider):
    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        return f"[FAKE_LLM_RESPONSE based on prompt of {len(prompt)} chars]"
