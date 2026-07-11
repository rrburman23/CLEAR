# src/agent/model_adapter.py
"""
CLEAR LLM Configuration and Adapter Layer

Handles initialization of the language model engine and performs critical
message-history sanitization. This module intercepts LangGraph state arrays
and scrubs them of natively incompatible data structures (e.g., ToolMessages)
before transmission to strict REST APIs like Ollama.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Sequence, Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_ollama import ChatOllama

from src.agent.candidate import normalise_args, parse_tool_payload
from src.agent.prompts import get_system_prompt
from src.tools.agent_tools import run_repair_attempt
from src.utils.config import (
    MODEL_NAME,
    OLLAMA_BASE_URL,
    SUPPORTS_NATIVE_TOOLS,
    USE_REAL_LLM,
)


def initialize_engines() -> tuple[Any, Any]:
    """Instantiates the required LangChain bindings based on environment capabilities."""
    if USE_REAL_LLM:
        base_llm = ChatOllama(
            model=MODEL_NAME,
            base_url=OLLAMA_BASE_URL,
            temperature=0,
        )
        native_llm = (
            base_llm.bind_tools([run_repair_attempt]) if SUPPORTS_NATIVE_TOOLS else None
        )
        return base_llm, native_llm

    class MockLLM:
        """Isolated development mock to prevent GPU binding overhead during unit tests."""

        def invoke(self, messages: Sequence[BaseMessage]) -> AIMessage:
            return AIMessage(
                content="```python\ndef mock_repair():\n    return True\n```"
            )

    return MockLLM(), None


base_llm, native_llm = initialize_engines()


def sanitize_messages_for_engine(
    messages: Sequence[BaseMessage], supports_native: bool
) -> list[BaseMessage]:
    """
    Orchestrates the context window format.
    Native models receive full ToolMessage history. Non-native models receive
    flattened Human/AI conversational transcripts to prevent HTTP 400 rejection.
    """
    system_prompt = get_system_prompt(supports_native)

    # Ensure optimal system prompt placement
    output_messages = list(messages)
    if not output_messages or not isinstance(output_messages[0], SystemMessage):
        output_messages.insert(0, SystemMessage(content=system_prompt))
    else:
        output_messages[0] = SystemMessage(content=system_prompt)

    if supports_native:
        return output_messages

    # Deep-sanitize history for text-only processing
    safe_messages = []
    for msg in output_messages:
        if isinstance(msg, AIMessage):
            tool_calls = getattr(msg, "tool_calls", None) or []
            if tool_calls:
                call = tool_calls[0]
                args = normalise_args(call.get("args", {}))
                submitted_code = args.get("code", "")

                safe_messages.append(
                    AIMessage(
                        content=(
                            "Previous candidate submitted:\n"
                            "```python\n"
                            f"{submitted_code}\n"
                            "```"
                        )
                    )
                )
            else:
                safe_messages.append(msg)

        elif isinstance(msg, ToolMessage):
            payload = parse_tool_payload(msg)
            if payload:
                feedback = {
                    "status": payload.get("status"),
                    "message": payload.get("message"),
                    "error": payload.get("error"),
                    "output": payload.get("output"),
                }
                safe_messages.append(
                    HumanMessage(
                        content=(
                            "SANDBOX FEEDBACK FOR THE PREVIOUS CANDIDATE:\n"
                            f"{json.dumps(feedback, ensure_ascii=False)}\n\n"
                            "Return a revised complete target.py inside one Python code block."
                        )
                    )
                )
            else:
                safe_messages.append(
                    HumanMessage(
                        content=(
                            "SANDBOX FEEDBACK:\n"
                            f"{msg.content}\n\n"
                            "Return a revised complete target.py."
                        )
                    )
                )
        else:
            safe_messages.append(msg)

    return safe_messages


def invoke_model(messages: Sequence[BaseMessage]) -> tuple[AIMessage, bool]:
    """
    Dispatches execution to the optimal LLM backend.
    Implements a resilient failover mechanism: if a native-bound model abruptly
    rejects tools mid-generation, it silently cascades down to the text engine.
    """
    if native_llm is not None:
        try:
            response = native_llm.invoke(sanitize_messages_for_engine(messages, True))
            return response, False
        except Exception as exc:
            error_text = str(exc).lower()
            tool_support_error = "does not support tools" in error_text or (
                "status code: 400" in error_text and "tool" in error_text
            )

            if not tool_support_error:
                raise

            if os.getenv("DEBUG"):
                print(
                    "Native tool calling rejected; falling back to text compatibility mode:",
                    exc,
                    file=sys.stderr,
                )

    # Fallback to pure text completion
    response = base_llm.invoke(sanitize_messages_for_engine(messages, False))
    return response, True
