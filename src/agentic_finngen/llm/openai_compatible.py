"""Adapter for any provider speaking the OpenAI /chat/completions dialect.

One adapter covers OpenAI itself plus every vendor that mirrors its wire format
(xAI, DeepSeek, Mistral, Groq, Together, OpenRouter, and local vLLM/Ollama
servers). The provider is selected by base URL and API key, both supplied by the
registry in `agentic_finngen.llm`.
"""
from __future__ import annotations

import json
import os
from typing import Any, Optional

try:
    from openai import OpenAI
except ImportError as exc:  # pragma: no cover - depends on optional extra
    raise RuntimeError(
        "The OpenAI-compatible providers require the 'openai' package. "
        "Install it with: pip install openai"
    ) from exc

from agentic_finngen.llm.base import Message, Response, Tool, ToolCall
from agentic_finngen.logger import get_logger

logger = get_logger(__name__)


def _tool_to_openai(tool: Tool) -> dict:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.input_schema,
        },
    }


def _messages_to_openai(
    messages: list[Message], system: Optional[str] = None
) -> list[dict]:
    """Translate our Message list into OpenAI's flat `messages` array."""
    out: list[dict] = []
    if system:
        out.append({"role": "system", "content": system})

    for msg in messages:
        if msg.role == "user":
            out.append({"role": "user", "content": msg.text or ""})
        elif msg.role == "assistant":
            entry: dict[str, Any] = {"role": "assistant"}
            # An assistant turn carries text, tool calls, or both; `content` must
            # still be present (as null) when only tool calls were returned.
            entry["content"] = msg.text or None
            if msg.tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.args or {}),
                        },
                    }
                    for tc in msg.tool_calls
                ]
            out.append(entry)
        elif msg.role == "tool":
            out.append(
                {
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id or "",
                    "content": msg.tool_result or "",
                }
            )
    return out


def _parse_arguments(raw: Optional[str], tool_name: str) -> dict:
    """Tool arguments arrive as a JSON string, and models sometimes emit junk."""
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning(
            "Could not parse arguments for tool '%s': %.200s", tool_name, raw
        )
        return {}
    return parsed if isinstance(parsed, dict) else {"value": parsed}


class OpenAICompatibleClient:
    def __init__(
        self,
        model_name: str,
        api_key_env: str,
        base_url: Optional[str] = None,
        provider_label: str = "OpenAI-compatible",
        max_tokens: Optional[int] = None,
    ):
        api_key = os.getenv(api_key_env)
        if not api_key:
            raise RuntimeError(
                f"Set {api_key_env} to use the {provider_label} provider."
            )
        self.model_name = model_name
        self.provider_label = provider_label
        self.max_tokens = max_tokens
        # Endpoints differ only by base URL; None means api.openai.com.
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._token_param = "max_completion_tokens"

    def _create(self, kwargs: dict):
        """Send the request, coping with the two spellings of the token cap.

        Newer OpenAI models require `max_completion_tokens`; several compatible
        vendors only accept the older `max_tokens`. Try the modern name first and
        fall back once, remembering the answer.
        """
        if self.max_tokens is None:
            return self._client.chat.completions.create(**kwargs)

        attempts = [self._token_param]
        if self._token_param == "max_completion_tokens":
            attempts.append("max_tokens")

        last_error: Optional[Exception] = None
        for param in attempts:
            try:
                response = self._client.chat.completions.create(
                    **kwargs, **{param: self.max_tokens}
                )
            except Exception as exc:  # noqa: BLE001 - provider-specific 400s
                if param not in str(exc):
                    raise
                logger.debug("Provider rejected '%s'; trying fallback.", param)
                last_error = exc
                continue
            self._token_param = param
            return response
        raise last_error  # type: ignore[misc]

    def complete(
        self,
        messages: list[Message],
        tools: Optional[list[Tool]] = None,
        system: Optional[str] = None,
    ) -> Response:
        kwargs: dict = {
            "model": self.model_name,
            "messages": _messages_to_openai(messages, system),
        }
        if tools:
            kwargs["tools"] = [_tool_to_openai(t) for t in tools]

        raw = self._create(kwargs)

        if not raw.choices:
            return Response(text="", tool_calls=[])
        message = raw.choices[0].message

        tool_calls: list[ToolCall] = []
        for call in getattr(message, "tool_calls", None) or []:
            function = getattr(call, "function", None)
            if function is None or not function.name:
                continue
            tool_calls.append(
                ToolCall(
                    id=call.id,
                    name=function.name,
                    args=_parse_arguments(function.arguments, function.name),
                )
            )

        return Response(text=message.content or "", tool_calls=tool_calls)

    def list_models(self) -> list[str]:
        return sorted(model.id for model in self._client.models.list())
