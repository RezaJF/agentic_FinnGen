"""Provider-neutral LLM client factory.

Selects an adapter based on env vars:
  LLM_PROVIDER  -- 'claude' (default) or 'gemini'
  LLM_MODEL     -- model id; falls back to a sensible per-provider default
"""
from __future__ import annotations

import os
from typing import Optional

from agentic_finngen.llm.base import LLMClient, Message, Response, Tool, ToolCall

__all__ = ["make_client", "LLMClient", "Message", "Response", "Tool", "ToolCall"]


_DEFAULT_MODELS = {
    "claude": "claude-sonnet-4-6",
    "anthropic": "claude-sonnet-4-6",
    "gemini": "gemini-1.5-pro-latest",
    "google": "gemini-1.5-pro-latest",
}


def make_client(
    provider: Optional[str] = None, model: Optional[str] = None
) -> LLMClient:
    provider = (provider or os.getenv("LLM_PROVIDER") or "claude").lower()
    model = model or os.getenv("LLM_MODEL") or _DEFAULT_MODELS.get(provider)
    if not model:
        raise RuntimeError(f"No model configured for provider '{provider}'.")

    if provider in ("claude", "anthropic"):
        from agentic_finngen.llm.anthropic import AnthropicClient

        return AnthropicClient(model)
    if provider in ("gemini", "google"):
        from agentic_finngen.llm.gemini import GeminiClient

        return GeminiClient(model)

    raise RuntimeError(
        f"Unknown LLM_PROVIDER '{provider}'. Expected 'claude' or 'gemini'."
    )
