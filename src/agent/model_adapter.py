"""
CLEAR LLM Adapter

Initialises the configured Ollama model and adapts graph message history for:

- models supporting native tool calls;
- text-only models requiring a compatibility layer.

The adapter does not perform candidate tracking. Candidate tracking belongs
to the graph's agent node after the final executable tool call is constructed.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping
from typing import Any, Sequence

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_ollama import ChatOllama

from src.agent.candidate import (
    normalise_args,
    parse_tool_payload,
)
from src.agent.prompts import get_system_prompt
from src.tools.agent_tools import run_repair_attempt
from src.utils.config import (
    MODEL_NAME,
    OLLAMA_BASE_URL,
    SUPPORTS_NATIVE_TOOLS,
    USE_REAL_LLM,
)


# =========================================================
# Model Initialisation
# =========================================================


class MockLLM:
    """
    Development-only model used when real inference is disabled.
    """

    def invoke(
        self,
        messages: Sequence[BaseMessage],
    ) -> AIMessage:
        del messages

        return AIMessage(
            content=("```python\ndef mock_repair():\n    return True\n```")
        )


def initialize_engines() -> tuple[Any, Any | None]:
    """
    Initialise the base model and optional native-tool binding.
    """

    if not USE_REAL_LLM:
        return MockLLM(), None

    base_engine: Any = ChatOllama(
        model=MODEL_NAME,
        base_url=OLLAMA_BASE_URL,
        temperature=0,
    )

    native_engine: Any | None = None

    if SUPPORTS_NATIVE_TOOLS:
        native_engine = base_engine.bind_tools([run_repair_attempt])

    return base_engine, native_engine


base_llm, native_llm = initialize_engines()


# =========================================================
# Response Normalisation
# =========================================================


def ensure_ai_message(
    response: Any,
) -> AIMessage:
    """
    Convert an arbitrary LangChain model response into an AIMessage.
    """

    if isinstance(response, AIMessage):
        return response

    content = getattr(
        response,
        "content",
        response,
    )

    return AIMessage(content=str(content))


# =========================================================
# Message History Adaptation
# =========================================================


def sanitize_messages_for_engine(
    messages: Sequence[BaseMessage],
    supports_native: bool,
) -> list[BaseMessage]:
    """
    Adapt graph history for the selected model interface.

    Native models receive structured ToolMessage history. Text-only models
    receive equivalent HumanMessage feedback so Ollama is not sent unsupported
    tool protocol objects.
    """

    system_prompt = get_system_prompt(supports_native)

    output_messages = list(messages)

    if not output_messages or not isinstance(
        output_messages[0],
        SystemMessage,
    ):
        output_messages.insert(
            0,
            SystemMessage(content=system_prompt),
        )
    else:
        output_messages[0] = SystemMessage(content=system_prompt)

    if supports_native:
        return output_messages

    safe_messages: list[BaseMessage] = []

    for message in output_messages:
        if isinstance(message, AIMessage):
            tool_calls = (
                getattr(
                    message,
                    "tool_calls",
                    None,
                )
                or []
            )

            if not tool_calls:
                safe_messages.append(message)
                continue

            first_call = tool_calls[0]

            arguments = normalise_args(
                first_call.get(
                    "args",
                    {},
                )
            )

            submitted_code = arguments.get(
                "code",
                "",
            )

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

            continue

        if isinstance(message, ToolMessage):
            payload = parse_tool_payload(message)

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
                            "Analyse this feedback and return a revised complete "
                            "target.py inside one Python code block. Do not "
                            "include framework code or the test suite."
                        )
                    )
                )

            else:
                safe_messages.append(
                    HumanMessage(
                        content=(
                            "SANDBOX FEEDBACK:\n"
                            f"{message.content}\n\n"
                            "Return a revised complete target.py inside one "
                            "Python code block."
                        )
                    )
                )

            continue

        safe_messages.append(message)

    return safe_messages


# =========================================================
# Candidate Extraction
# =========================================================


def get_candidate_code(
    response: AIMessage,
) -> str | None:
    """
    Extract candidate source from a run_repair_attempt tool call.
    """

    tool_calls = (
        getattr(
            response,
            "tool_calls",
            None,
        )
        or []
    )

    for tool_call in tool_calls:
        if not isinstance(
            tool_call,
            Mapping,
        ):
            continue

        if tool_call.get("name") != "run_repair_attempt":
            continue

        arguments = tool_call.get(
            "args",
            {},
        )

        if not isinstance(
            arguments,
            Mapping,
        ):
            continue

        candidate_code = arguments.get("code")

        if isinstance(candidate_code, str) and candidate_code.strip():
            return candidate_code

    return None


# =========================================================
# Model Invocation
# =========================================================


def invoke_model(
    messages: Sequence[BaseMessage],
) -> tuple[AIMessage, bool]:
    """
    Invoke the configured model.

    Returns:
        A tuple containing:

        - the AI response;
        - whether text compatibility mode was used.

    If Ollama rejects native tool calling, CLEAR falls back to ordinary text
    completion for that response.
    """

    if native_llm is not None:
        try:
            native_response = native_llm.invoke(
                sanitize_messages_for_engine(
                    messages,
                    True,
                )
            )

            return (
                ensure_ai_message(native_response),
                False,
            )

        except Exception as exc:
            error_text = str(exc).lower()

            tool_support_error = "does not support tools" in error_text or (
                "status code: 400" in error_text and "tool" in error_text
            )

            if not tool_support_error:
                raise

            if os.getenv("DEBUG"):
                print(
                    (
                        "Native tool calling rejected; "
                        "falling back to text compatibility mode:"
                    ),
                    exc,
                    file=sys.stderr,
                )

    text_response = base_llm.invoke(
        sanitize_messages_for_engine(
            messages,
            False,
        )
    )

    return (
        ensure_ai_message(text_response),
        True,
    )
