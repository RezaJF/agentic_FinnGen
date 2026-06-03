"""Explicit tool-use loop that drives an LLMClient until it emits a final text."""
from __future__ import annotations

import json
from typing import Optional

from agentic_finngen.llm.base import LLMClient, Message, Tool
from agentic_finngen.logger import get_logger

logger = get_logger(__name__)


def run_tool_loop(
    client: LLMClient,
    messages: list[Message],
    tools: list[Tool],
    system: Optional[str] = None,
    max_iters: int = 50,
) -> str:
    """Call the model; if it requests tool calls, run them and feed results back."""
    tool_index = {t.name: t for t in tools}

    for _ in range(max_iters):
        response = client.complete(messages, tools=tools, system=system)
        logger.debug("%s", response)
        if not response.tool_calls:
            return response.text

        messages.append(Message(role="assistant", tool_calls=response.tool_calls))

        for tc in response.tool_calls:
            tool = tool_index.get(tc.name)
            if tool is None:
                result = f"Error: unknown tool '{tc.name}'"
            else:
                try:
                    raw = tool.fn(**tc.args)
                    result = raw if isinstance(raw, str) else json.dumps(raw, default=str)
                    logger.debug("Tool '%s' returned: %s", tc.name, result)
                except Exception as exc:  # surface errors back to the model
                    result = f"Error invoking {tc.name}: {exc}"
            messages.append(
                Message(role="tool", tool_call_id=tc.id, tool_result=result)
            )

    return "Error: tool loop exceeded max iterations"
