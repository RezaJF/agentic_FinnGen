"""Anthropic Claude adapter for the LLMClient protocol."""
from __future__ import annotations

import os
from typing import Optional

import anthropic

from agentic_finngen.llm.base import Message, Response, Tool, ToolCall


DEFAULT_MAX_TOKENS = 4096


def _tool_to_anthropic(tool: Tool) -> dict:
    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.input_schema,
    }


def _messages_to_anthropic(messages: list[Message]) -> list[dict]:
    """Translate our Message list into Anthropic's `messages` shape."""
    out: list[dict] = []
    pending_tool_results: list[dict] = []

    def flush_tool_results() -> None:
        if pending_tool_results:
            out.append({"role": "user", "content": list(pending_tool_results)})
            pending_tool_results.clear()

    for msg in messages:
        if msg.role == "user":
            flush_tool_results()
            out.append({"role": "user", "content": msg.text or ""})
        elif msg.role == "assistant":
            flush_tool_results()
            blocks: list[dict] = []
            if msg.text:
                blocks.append({"type": "text", "text": msg.text})
            for tc in msg.tool_calls or []:
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.args,
                    }
                )
            out.append({"role": "assistant", "content": blocks})
        elif msg.role == "tool":
            pending_tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": msg.tool_call_id or "",
                    "content": msg.tool_result or "",
                }
            )

    flush_tool_results()
    return out


class AnthropicClient:
    def __init__(self, model_name: str, max_tokens: int = DEFAULT_MAX_TOKENS):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Set ANTHROPIC_API_KEY to use the Anthropic provider."
            )
        self.model_name = model_name
        self.max_tokens = max_tokens
        self._client = anthropic.Anthropic(api_key=api_key)

    def complete(
        self,
        messages: list[Message],
        tools: Optional[list[Tool]] = None,
        system: Optional[str] = None,
    ) -> Response:
        kwargs: dict = {
            "model": self.model_name,
            "max_tokens": self.max_tokens,
            "messages": _messages_to_anthropic(messages),
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = [_tool_to_anthropic(t) for t in tools]

        raw = self._client.messages.create(**kwargs)

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in raw.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, args=dict(block.input))
                )

        return Response(text="".join(text_parts), tool_calls=tool_calls)
