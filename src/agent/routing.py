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
    End after verified sandbox success or return failure feedback to the model.
    """

    last_message = state["messages"][-1]

    if not isinstance(
        last_message,
        ToolMessage,
    ):
        return "agent"

    payload = parse_tool_payload(last_message)

    candidate_code = payload.get("code") if payload else None

    if (
        payload
        and payload.get("status") == "SUCCESS"
        and isinstance(candidate_code, str)
        and candidate_code.strip()
    ):
        return "end"

    return "agent"
