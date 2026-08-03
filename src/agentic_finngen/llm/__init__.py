"""Provider-neutral LLM client factory.

Selects an adapter from env vars, so switching frontier labs is a config change
rather than a code change:

  LLM_PROVIDER   -- provider key, e.g. 'anthropic', 'gemini', 'openai', 'xai'
  LLM_MODEL      -- model id; falls back to the provider's default where known
  LLM_BASE_URL   -- override the provider endpoint (required for 'openai-compatible')
  LLM_MAX_TOKENS -- optional output cap

Run `agentic-finngen --list-providers` to see the table, or `--list-models` to
ask the configured provider which models your key can actually reach.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from agentic_finngen.llm.base import LLMClient, Message, Response, Tool, ToolCall

__all__ = [
    "make_client",
    "list_providers",
    "describe_providers",
    "resolve_provider",
    "LLMClient",
    "Message",
    "Response",
    "Tool",
    "ToolCall",
]


@dataclass(frozen=True)
class Provider:
    """How to reach one vendor's API."""

    key: str
    label: str
    # 'anthropic' and 'gemini' have native SDKs; everything else speaks the
    # OpenAI /chat/completions dialect and differs only by base URL.
    kind: str
    api_key_env: str
    default_model: Optional[str] = None
    base_url: Optional[str] = None
    aliases: tuple[str, ...] = field(default_factory=tuple)
    notes: str = ""


# Default models are only set where a current, function-calling-capable id is
# known. Elsewhere LLM_MODEL is required rather than guessed, because a stale
# default surfaces as a confusing 404 on the first API call.
_PROVIDERS: tuple[Provider, ...] = (
    Provider(
        key="anthropic",
        label="Anthropic Claude",
        kind="anthropic",
        api_key_env="ANTHROPIC_API_KEY",
        default_model="claude-opus-5",
        aliases=("claude",),
    ),
    Provider(
        key="gemini",
        label="Google Gemini",
        kind="gemini",
        api_key_env="GEMINI_API_KEY",
        default_model="gemini-2.5-pro",
        aliases=("google",),
        notes="Or set GOOGLE_GENAI_USE_VERTEXAI=true for Vertex AI with ADC.",
    ),
    Provider(
        key="openai",
        label="OpenAI",
        kind="openai",
        api_key_env="OPENAI_API_KEY",
        aliases=("gpt",),
    ),
    Provider(
        key="xai",
        label="xAI Grok",
        kind="openai",
        api_key_env="XAI_API_KEY",
        base_url="https://api.x.ai/v1",
        aliases=("grok",),
    ),
    Provider(
        key="deepseek",
        label="DeepSeek",
        kind="openai",
        api_key_env="DEEPSEEK_API_KEY",
        base_url="https://api.deepseek.com/v1",
    ),
    Provider(
        key="mistral",
        label="Mistral",
        kind="openai",
        api_key_env="MISTRAL_API_KEY",
        base_url="https://api.mistral.ai/v1",
    ),
    Provider(
        key="groq",
        label="Groq",
        kind="openai",
        api_key_env="GROQ_API_KEY",
        base_url="https://api.groq.com/openai/v1",
    ),
    Provider(
        key="together",
        label="Together AI",
        kind="openai",
        api_key_env="TOGETHER_API_KEY",
        base_url="https://api.together.xyz/v1",
    ),
    Provider(
        key="openrouter",
        label="OpenRouter",
        kind="openai",
        api_key_env="OPENROUTER_API_KEY",
        base_url="https://openrouter.ai/api/v1",
        notes="Fronts most frontier models; ids look like 'vendor/model'.",
    ),
    Provider(
        key="openai-compatible",
        label="Any OpenAI-compatible endpoint",
        kind="openai",
        api_key_env="LLM_API_KEY",
        aliases=("compatible", "local"),
        notes="Set LLM_BASE_URL and LLM_MODEL; for local servers any key works.",
    ),
)

_BY_NAME: dict[str, Provider] = {}
for _provider in _PROVIDERS:
    _BY_NAME[_provider.key] = _provider
    for _alias in _provider.aliases:
        _BY_NAME[_alias] = _provider


def list_providers() -> list[str]:
    return [provider.key for provider in _PROVIDERS]


def describe_providers() -> str:
    """A human-readable table for `--list-providers`."""
    rows = [("PROVIDER", "API KEY VARIABLE", "DEFAULT MODEL")]
    rows += [
        (p.key, p.api_key_env, p.default_model or "(set LLM_MODEL)")
        for p in _PROVIDERS
    ]
    widths = [max(len(row[i]) for row in rows) for i in range(3)]
    lines = [
        "  ".join(value.ljust(widths[i]) for i, value in enumerate(row)).rstrip()
        for row in rows
    ]
    for provider in _PROVIDERS:
        if provider.notes:
            lines.append(f"    {provider.key}: {provider.notes}")
    return "\n".join(lines)


def resolve_provider(name: Optional[str] = None) -> Provider:
    key = (name or os.getenv("LLM_PROVIDER") or "anthropic").strip().lower()
    provider = _BY_NAME.get(key)
    if provider is None:
        raise RuntimeError(
            f"Unknown LLM_PROVIDER '{key}'. Expected one of: "
            f"{', '.join(list_providers())}."
        )
    return provider


def _max_tokens() -> Optional[int]:
    raw = (os.getenv("LLM_MAX_TOKENS") or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        raise RuntimeError(f"LLM_MAX_TOKENS must be an integer, got '{raw}'.")


def make_client(
    provider: Optional[str] = None, model: Optional[str] = None
) -> LLMClient:
    spec = resolve_provider(provider)

    model = model or os.getenv("LLM_MODEL") or spec.default_model
    if not model:
        raise RuntimeError(
            f"No default model for provider '{spec.key}'. Set LLM_MODEL to a "
            f"model id offered by {spec.label}, then use --list-models to "
            "confirm your key can reach it."
        )

    max_tokens = _max_tokens()

    if spec.kind == "anthropic":
        from agentic_finngen.llm.anthropic import AnthropicClient

        if max_tokens is not None:
            return AnthropicClient(model, max_tokens=max_tokens)
        return AnthropicClient(model)

    if spec.kind == "gemini":
        from agentic_finngen.llm.gemini import GeminiClient

        return GeminiClient(model)

    base_url = os.getenv("LLM_BASE_URL") or spec.base_url
    if spec.key == "openai-compatible" and not base_url:
        raise RuntimeError(
            "Provider 'openai-compatible' requires LLM_BASE_URL (for example "
            "http://localhost:11434/v1 for Ollama)."
        )

    from agentic_finngen.llm.openai_compatible import OpenAICompatibleClient

    return OpenAICompatibleClient(
        model,
        api_key_env=spec.api_key_env,
        base_url=base_url,
        provider_label=spec.label,
        max_tokens=max_tokens,
    )
