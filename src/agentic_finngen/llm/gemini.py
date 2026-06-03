"""Gemini adapter for the LLMClient protocol."""
from __future__ import annotations

import os
import uuid
from typing import Optional

from google import genai
from google.genai import types

from agentic_finngen.llm.base import Message, Response, Tool, ToolCall


_client: Optional[genai.Client] = None


def _truthy(v: Optional[str]) -> bool:
    return (v or "").strip().lower() in {"1", "true", "yes", "on"}


def _ensure_client() -> genai.Client:
    global _client
    if _client is not None:
        return _client

    if _truthy(os.getenv("GOOGLE_GENAI_USE_VERTEXAI")):
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_LOCATION")
        missing = [
            name
            for name, value in (
                ("GOOGLE_CLOUD_PROJECT", project),
                ("GOOGLE_CLOUD_LOCATION", location),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(
                f"GOOGLE_GENAI_USE_VERTEXAI=true requires: {', '.join(missing)}. "
                "Ensure Application Default Credentials are configured via "
                "`gcloud auth application-default login` or GOOGLE_APPLICATION_CREDENTIALS."
            )
        _client = genai.Client(vertexai=True, project=project, location=location)
    else:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("VERTEX_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Set GEMINI_API_KEY for API-key auth, or set "
                "GOOGLE_GENAI_USE_VERTEXAI=true with GOOGLE_CLOUD_PROJECT and "
                "GOOGLE_CLOUD_LOCATION for Vertex AI with Application Default Credentials."
            )
        _client = genai.Client(api_key=api_key)
    return _client


def _tool_to_gemini(tool: Tool) -> dict:
    return {
        "name": tool.name,
        "description": tool.description,
        "parameters": tool.input_schema,
    }


def _messages_to_contents(messages: list[Message]) -> list[dict]:
    """Translate our Message list into Gemini's `contents` shape."""
    contents: list[dict] = []
    for msg in messages:
        if msg.role == "user":
            contents.append({"role": "user", "parts": [{"text": msg.text or ""}]})
        elif msg.role == "assistant":
            parts: list[dict] = []
            if msg.text:
                parts.append({"text": msg.text})
            for tc in msg.tool_calls or []:
                part = {"function_call": {"name": tc.name, "args": tc.args}}
                sig = (tc.metadata or {}).get("thought_signature")
                if sig:
                    part["thought_signature"] = sig
                parts.append(part)
            contents.append({"role": "model", "parts": parts})
        elif msg.role == "tool":
            # Gemini routes tool results back via a "user" turn with function_response.
            # The function name is recovered from the matching prior function_call.
            tool_name = _find_tool_name_for_id(messages, msg.tool_call_id)
            contents.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "function_response": {
                                "name": tool_name,
                                "response": {"result": msg.tool_result or ""},
                            }
                        }
                    ],
                }
            )
    return contents


def _find_tool_name_for_id(messages: list[Message], tool_call_id: Optional[str]) -> str:
    if not tool_call_id:
        return ""
    for msg in messages:
        for tc in msg.tool_calls or []:
            if tc.id == tool_call_id:
                return tc.name
    return ""


class GeminiClient:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._client = _ensure_client()

    def complete(
        self,
        messages: list[Message],
        tools: Optional[list[Tool]] = None,
        system: Optional[str] = None,
    ) -> Response:
        config_kwargs: dict = {
            "automatic_function_calling": types.AutomaticFunctionCallingConfig(
                disable=True
            ),
        }
        if system:
            config_kwargs["system_instruction"] = system
        if tools:
            config_kwargs["tools"] = [
                types.Tool(
                    function_declarations=[_tool_to_gemini(t) for t in tools]
                )
            ]

        raw = self._client.models.generate_content(
            model=self.model_name,
            contents=_messages_to_contents(messages),
            config=types.GenerateContentConfig(**config_kwargs),
        )

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for cand in getattr(raw, "candidates", []) or []:
            for part in getattr(cand.content, "parts", []) or []:
                fc = getattr(part, "function_call", None)
                if fc and fc.name:
                    meta: dict = {}
                    sig = getattr(part, "thought_signature", None)
                    if sig:
                        meta["thought_signature"] = sig
                    tool_calls.append(
                        ToolCall(
                            id=f"gemini-{uuid.uuid4().hex[:12]}",
                            name=fc.name,
                            args=dict(fc.args) if fc.args else {},
                            metadata=meta,
                        )
                    )
                elif getattr(part, "text", None):
                    text_parts.append(part.text)

        return Response(text="".join(text_parts), tool_calls=tool_calls)
