"""
LLM client for integrating with Claude or OpenAI API.

Supports both providers with API key management via environment variables.
For the demo, results are formatted and displayed without actual API calls.
"""

import os
from typing import Optional
from enum import Enum


class LLMProvider(Enum):
    """Supported LLM providers."""
    CLAUDE = "claude"
    OPENAI = "openai"


class LLMClient:
    """
    Thin wrapper for LLM API calls.
    
    Supports Claude (via Anthropic) and OpenAI.
    API keys are read from environment variables.
    """

    def __init__(self, provider: LLMProvider = LLMProvider.CLAUDE, model: Optional[str] = None):
        """
        Initialize LLM client.

        Args:
            provider: LLMProvider enum value (CLAUDE or OPENAI)
            model: Specific model to use (optional). Defaults:
                   - Claude: "claude-3-haiku-20250122"
                   - OpenAI: "gpt-4"
        """
        self.provider = provider
        self.model = model or self._get_default_model()
        self.api_key = self._get_api_key()

    def _get_default_model(self) -> str:
        """Get default model for the provider."""
        if self.provider == LLMProvider.CLAUDE:
            return "claude-3-haiku-20250122"
        elif self.provider == LLMProvider.OPENAI:
            return "gpt-4"
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def _get_api_key(self) -> Optional[str]:
        """
        Retrieve API key from environment variables.

        For Claude: ANTHROPIC_API_KEY
        For OpenAI: OPENAI_API_KEY

        Returns:
            API key string or None if not found
        """
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
        """
        Query the LLM with retrieved context.

        For demo purposes, this returns a formatted response without actual API calls.
        In production, this would integrate with the actual LLM API.

        Args:
            context: Retrieved context (FAQs) to pass to LLM
            question: User's original question

        Returns:
            LLM response as a string
        """
        if not self.api_key:
            # Demo mode: return a simple structured response
            return self._demo_response(question, context)

        # In production, actual API calls would go here
        # For now, we'll still use demo mode
        return self._demo_response(question, context)

    def _demo_response(self, question: str, context: str) -> str:
        """
        Generate a demo response showing how LLM would be called.

        Args:
            question: User's question
            context: Retrieved context

        Returns:
            Formatted demo response
        """
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
"""
        return response.strip()


def create_llm_client(provider_name: str = "claude") -> LLMClient:
    """
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
