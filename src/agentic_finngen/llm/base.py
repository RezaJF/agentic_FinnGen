"""Provider-neutral types for the LLM abstraction."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict
    fn: Callable[..., Any]


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict
    metadata: dict = field(default_factory=dict)


@dataclass
class Message:
    role: str  # "user" | "assistant" | "tool"
    text: Optional[str] = None
    tool_calls: Optional[list[ToolCall]] = None
    tool_call_id: Optional[str] = None
    tool_result: Optional[str] = None


@dataclass
class Response:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMClient(Protocol):
    model_name: str

    def complete(
        self,
        messages: list[Message],
        tools: Optional[list[Tool]] = None,
        system: Optional[str] = None,
    ) -> Response: ...
