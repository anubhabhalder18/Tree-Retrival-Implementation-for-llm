
import os
from typing import Optional
from enum import Enum
class LLMProvider(Enum):
    CLAUDE = "claude"
    OPENAI = "openai"
class LLMClient:
    def __init__(self, provider: LLMProvider = LLMProvider.CLAUDE, model: Optional[str] = None):
        self.provider = provider
        self.model = model or self._get_default_model()
        self.api_key = self._get_api_key()
    def _get_default_model(self) -> str:
        if self.provider == LLMProvider.CLAUDE:
            return "claude-3-haiku-20250122"
        elif self.provider == LLMProvider.OPENAI:
            return "gpt-4"
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    def _get_api_key(self) -> Optional[str]:
        if self.provider == LLMProvider.CLAUDE:
            key = os.getenv("ANTHROPIC_API_KEY")
            if not key:
                print("⚠️  ANTHROPIC_API_KEY not set. Defaulting to demo mode (no actual API calls).")
            return key
        elif self.provider == LLMProvider.OPENAI:
            key = os.getenv("OPENAI_API_KEY")
            if not key:
                print("⚠️  OPENAI_API_KEY not set. Defaulting to demo mode (no actual API calls).")
            return key
        return None
    def query(self, context: str, question: str) -> str:
        if not self.api_key:
            return self._demo_response(question, context)
        return self._demo_response(question, context)
    def _demo_response(self, question: str, context: str) -> str:
        response = f"""
[LLM Response - Demo Mode]
Provider: {self.provider.value.upper()}
Model: {self.model}
Question:
{question}
Context Used:
{context}
Response:
Based on the retrieved context above, here is an answer to your question:
[LLM would generate a response here based on the context and question]
Note: This is a demo response. In production with API credentials,
this would call the actual {self.provider.value.upper()} API.
    Factory function to create an LLM client.
    Args:
        provider_name: "claude" or "openai"
    Returns:
        LLMClient instance
    Raises:
        ValueError: If provider_name is not recognized
    """
    provider_map = {
        "claude": LLMProvider.CLAUDE,
        "openai": LLMProvider.OPENAI,
    }
    if provider_name.lower() not in provider_map:
        raise ValueError(f"Unknown provider: {provider_name}. Choose 'claude' or 'openai'.")
    return LLMClient(provider=provider_map[provider_name.lower()])
