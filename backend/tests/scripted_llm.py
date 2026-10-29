"""
Configurable fake LLM provider — returns whatever string you hand it,
so tests can simulate well-formed JSON, malformed JSON, or garbage output
from the classifier without a real Gemini call.
"""
from llm.provider import LLMProvider


class ScriptedLLMProvider(LLMProvider):
    def __init__(self, response: str):
        self._response = response

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        return self._response


class RaisingLLMProvider(LLMProvider):
    """Simulates an API failure (network error, rate limit, etc.)."""
    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        raise RuntimeError("simulated Gemini API failure")
