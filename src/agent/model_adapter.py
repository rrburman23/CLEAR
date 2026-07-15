"""
CLEAR Model Adapter

Provides one protocol-normalised inference path for all evaluated models.

The principal experiment does not use native tool calling. Every model receives
a compact repair prompt and returns Python source only.
"""

from __future__ import annotations

import logging
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
    parse_tool_payload,
    strip_reasoning_blocks,
)
from src.agent.prompts import (
    CODE_ONLY_SYSTEM_PROMPT,
    build_compact_repair_prompt,
)
from src.agent.state import AgentState
from src.utils.config import (
    MODEL_NAME,
    MODEL_PROFILE,
    OLLAMA_BASE_URL,
    USE_REAL_LLM,
)


# =========================================================
# Model Initialisation
# =========================================================


logger = logging.getLogger(__name__)


class MockLLM:
    """Development-only code-output model."""

    def invoke(
        self,
        messages: Sequence[BaseMessage],
    ) -> AIMessage:
        del messages

        return AIMessage(
            content=("```python\ndef placeholder() -> bool:\n    return True\n```")
        )


def initialise_model() -> Any:
    """
    Initialise one plain ChatOllama model.

    Deliberately does not call ``bind_tools``.
    """

    if not USE_REAL_LLM:
        return MockLLM()

    model_arguments: dict[str, Any] = {
        "model": MODEL_NAME,
        "base_url": OLLAMA_BASE_URL,
        "temperature": MODEL_PROFILE.temperature,
        "num_predict": MODEL_PROFILE.num_predict,
    }

    if MODEL_PROFILE.reasoning is not None:
        model_arguments["reasoning"] = MODEL_PROFILE.reasoning

    return ChatOllama(**model_arguments)

base_llm: Any = initialise_model()


# =========================================================
# Compact Sandbox Feedback
# =========================================================


def _latest_tool_message(
    state: AgentState,
) -> ToolMessage | None:
    """Return the most recent sandbox ToolMessage."""

    messages = state.get(
        "messages",
        [],
    )

    for message in reversed(messages):
        if isinstance(message, ToolMessage):
            return message

    return None


def _compact_tool_feedback(
    message: ToolMessage,
    *,
    maximum_characters: int,
) -> str:
    """
    Convert one sandbox payload into concise actionable feedback.

    The most recent tail is retained because pytest places its short test
    summary and final failure details near the end of the output.
    """

    payload = parse_tool_payload(message)

    if payload is None:
        feedback = str(message.content)
    else:
        parts: list[str] = []

        status = payload.get("status")

        if status:
            parts.append(f"Status: {status}")

        message_text = payload.get("message")

        if message_text:
            parts.append(f"Message: {message_text}")

        error_text = payload.get("error")

        output_text = payload.get("output")

        if error_text:
            parts.append(f"Failure details:\n{error_text}")

        if output_text and output_text != error_text:
            parts.append(f"Pytest output:\n{output_text}")

        feedback = "\n\n".join(parts)

    feedback = feedback.strip()

    if len(feedback) <= maximum_characters:
        return feedback

    return "[Earlier traceback content omitted]\n" + feedback[-maximum_characters:]


# =========================================================
# Prompt Reconstruction
# =========================================================


def build_compact_messages(
    state: AgentState,
) -> list[BaseMessage]:
    """
    Reconstruct a compact inference context from graph state.

    The full accumulated message history is deliberately not sent to Ollama.
    """

    latest_feedback = state.get("latest_feedback")

    latest_tool_message = _latest_tool_message(state)

    if latest_tool_message is not None:
        latest_feedback = _compact_tool_feedback(
            latest_tool_message,
            maximum_characters=(MODEL_PROFILE.max_feedback_characters),
        )

    user_prompt = build_compact_repair_prompt(
        original_code=state["original_code"],
        test_suite=state["test_suite"],
        latest_candidate=state.get("latest_candidate"),
        latest_feedback=latest_feedback,
    )

    return [
        SystemMessage(content=CODE_ONLY_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]


# =========================================================
# Inference
# =========================================================

def invoke_model(
    state: AgentState,
) -> AIMessage:
    """
    Invoke the selected model through the shared code-only protocol.

    Response telemetry is recorded before and after model-specific
    normalisation. Terminal response failures are attached to the returned
    message so the repair graph can stop rather than issuing identical,
    expensive retries.
    """

    messages = build_compact_messages(state)
    raw_response = base_llm.invoke(messages)

    if isinstance(raw_response, AIMessage):
        response = raw_response
    else:
        response = AIMessage(
            content=str(
                getattr(
                    raw_response,
                    "content",
                    raw_response,
                )
            )
        )

    raw_content = str(response.content or "")

    response_metadata = (
        getattr(
            response,
            "response_metadata",
            {},
        )
        or {}
    )

    additional_kwargs = (
        getattr(
            response,
            "additional_kwargs",
            {},
        )
        or {}
    )

    reasoning_content = str(
        additional_kwargs.get(
            "reasoning_content",
            "",
        )
        or ""
    )

    cleaned_content = raw_content

    if MODEL_PROFILE.strip_reasoning:
        cleaned_content = strip_reasoning_blocks(cleaned_content)

    cleaned_content = cleaned_content.strip()

    done_reason = str(
        response_metadata.get(
            "done_reason",
            "",
        )
        or ""
    )

    evaluation_count = response_metadata.get("eval_count")

    prompt_evaluation_count = response_metadata.get("prompt_eval_count")

    logger.info(
        (
            "Model response telemetry | Model=%s | "
            "RawChars=%d | CleanedChars=%d | "
            "ReasoningChars=%d | DoneReason=%s | "
            "EvalCount=%s | PromptEvalCount=%s"
        ),
        MODEL_PROFILE.name,
        len(raw_content),
        len(cleaned_content),
        len(reasoning_content),
        done_reason or "unknown",
        evaluation_count,
        prompt_evaluation_count,
    )
    
    failure_reason: str | None = None

    if not cleaned_content and done_reason == "length":
        failure_reason = (
            "Model generation limit exhausted before final repair payload"
        )

        logger.warning(
            "%s | Model=%s | NumPredict=%d | ReasoningChars=%d",
            failure_reason,
            MODEL_PROFILE.name,
            MODEL_PROFILE.num_predict,
            len(reasoning_content),
        )

    elif raw_content.strip() and not cleaned_content:
        failure_reason = (
            "Model response became empty after protocol normalisation"
        )

        logger.warning(
            "%s | Model=%s | RawChars=%d | ReasoningChars=%d",
            failure_reason,
            MODEL_PROFILE.name,
            len(raw_content),
            len(reasoning_content),
        )

        logger.debug(
            "Raw response removed during normalisation:\n%s",
            raw_content,
        )

    elif not cleaned_content:
        failure_reason = (
            "Model returned no executable final response content"
        )

        logger.warning(
            "%s | Model=%s | ReasoningChars=%d | DoneReason=%s",
            failure_reason,
            MODEL_PROFILE.name,
            len(reasoning_content),
            done_reason or "unknown",
        )

    message_metadata: dict[str, Any] = {
        "done_reason": done_reason,
        "eval_count": evaluation_count,
        "prompt_eval_count": prompt_evaluation_count,
        "reasoning_characters": len(reasoning_content),
    }

    if failure_reason is not None:
        message_metadata["clear_failure_reason"] = failure_reason

    return AIMessage(
        content=cleaned_content,
        additional_kwargs=message_metadata,
        response_metadata=response_metadata,
    )