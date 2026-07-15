"""
CLEAR Graph Routing

Defines deterministic transitions after model and tool nodes.
"""

from __future__ import annotations

from langchain_core.messages import AIMessage, ToolMessage

from src.agent.candidate import parse_tool_payload
from src.agent.state import AgentState


def route_after_agent(
    state: AgentState,
) -> str:
    """
    Route after model generation.

    A framework-detected terminal failure takes priority over a generated tool
    call. This prevents the third consecutive duplicate candidate from being
    executed again.
    """

    terminal_failure = state.get("terminal_failure")

    if isinstance(terminal_failure, str) and terminal_failure.strip():
        return "end"

    last_message = state["messages"][-1]

    if isinstance(
        last_message,
        AIMessage,
    ):
        tool_calls = (
            getattr(
                last_message,
                "tool_calls",
                None,
            )
            or []
        )

        if tool_calls:
            return "tools"

    return "agent"


def route_after_tools(
    state: AgentState,
) -> str:
    """
    Route after sandbox execution.

    - Verified candidates terminate successfully.
    - Infrastructure errors terminate without further model calls.
    - Ordinary test failures return feedback to the model.
    """

    last_message = state["messages"][-1]

    if not isinstance(last_message, ToolMessage):
        return "agent"

    payload = parse_tool_payload(last_message)

    if not payload:
        return "agent"

    status = payload.get("status")

    if status == "INFRASTRUCTURE_ERROR":
        return "infrastructure_error"

    candidate_code = payload.get("code")

    if (
        status == "SUCCESS"
        and isinstance(candidate_code, str)
        and candidate_code.strip()
    ):
        return "end"

    return "agent"


def get_model_failure_reason(
    state: AgentState,
) -> str | None:
    """
    Return a terminal failure reported by the model adapter.

    The adapter uses this metadata when the model exhausts its generation
    budget or returns no executable final response.
    """

    messages = state.get("messages", [])

    if not messages:
        return None

    latest_message = messages[-1]

    if not isinstance(latest_message, AIMessage):
        return None

    failure_reason = latest_message.additional_kwargs.get("clear_failure_reason")

    if not failure_reason:
        return None

    return str(failure_reason)
