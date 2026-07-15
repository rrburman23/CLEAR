"""
CLEAR Central Repair Orchestrator

Composes the code-only model adapter, internal tool-call conversion, sandbox
tool node, candidate tracking, and termination routing.
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import ToolMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from src.agent.candidate import (
    build_candidate_tracking_update,
    convert_text_response_to_tool_call,
    get_candidate_code,
    parse_tool_payload,
)
from src.agent.model_adapter import invoke_model
from src.agent.routing import (
    route_after_agent,
    route_after_tools,
)
from src.agent.state import AgentState
from src.tools.repair_tools import run_repair_attempt


MAX_INVALID_RESPONSES = 3

TOOLS = [
    run_repair_attempt,
]

tool_node = ToolNode(TOOLS)

def record_infrastructure_error(
    state: AgentState,
) -> dict[str, Any]:
    """
    Copy a sandbox infrastructure error into graph state.

    This prevents CLEAR from asking the model to repair a broken benchmark
    configuration.
    """

    messages = state.get("messages", [])

    if not messages:
        reason = "Unknown benchmark infrastructure failure."

        return {
            "terminal_failure": reason,
            "failure_reason": reason,
            "verified": False,
        }

    latest_message = messages[-1]

    if not isinstance(latest_message, ToolMessage):
        reason = "Expected an infrastructure ToolMessage but none was found."

        return {
            "terminal_failure": reason,
            "failure_reason": reason,
            "verified": False,
        }

    payload = parse_tool_payload(latest_message) or {}

    reason = str(
        payload.get("message")
        or payload.get("error")
        or "Benchmark infrastructure failure."
    )

    return {
        "terminal_failure": reason,
        "failure_reason": reason,
        "verified": False,
    }
    
    
def call_model(
    state: AgentState,
) -> dict[str, Any]:
    """
    Generate one candidate and convert it into an internal sandbox tool call.

    The selected model produces source code only. CLEAR creates the actual
    ``run_repair_attempt`` call with the canonical test suite.

    Model-adapter failures are copied directly into graph state so terminal
    generation failures stop immediately without additional model calls.
    """

    response = invoke_model(state)

    model_failure_reason = response.additional_kwargs.get("clear_failure_reason")

    if model_failure_reason:
        failure_reason = str(model_failure_reason)

        return {
            "messages": [response],
            "terminal_failure": failure_reason,
            "failure_reason": failure_reason,
            "verified": False,
        }

    converted_response = convert_text_response_to_tool_call(
        response_text=str(response.content),
        canonical_test_suite=state["test_suite"],
    )

    if converted_response is not None:
        candidate_code = get_candidate_code(converted_response)

        if candidate_code is not None:
            state_update: dict[str, Any] = {
                "messages": [converted_response],
                "latest_candidate": candidate_code,
                "latest_feedback": None,
                "invalid_responses": 0,
                "terminal_failure": None,
                "failure_reason": None,
            }

            tracking_update = build_candidate_tracking_update(
                state=state,
                candidate_code=candidate_code,
            )

            state_update.update(tracking_update)

            return state_update

    invalid_responses = (
        state.get(
            "invalid_responses",
            0,
        )
        + 1
    )

    protocol_feedback = (
        "The previous response could not be parsed as a complete valid "
        "Python program. Return exactly one Python Markdown code block "
        "containing the complete standalone target.py source. Do not "
        "include prose, JSON, tool calls, tests, or framework code."
    )

    if invalid_responses >= MAX_INVALID_RESPONSES:
        failure_reason = (
            "Model protocol failure: no executable repair payload "
            f"after {invalid_responses} responses"
        )

        return {
            "messages": [response],
            "latest_feedback": protocol_feedback,
            "invalid_responses": invalid_responses,
            "terminal_failure": failure_reason,
            "failure_reason": failure_reason,
            "verified": False,
        }

    return {
        "messages": [response],
        "latest_feedback": protocol_feedback,
        "invalid_responses": invalid_responses,
        "terminal_failure": None,
        "failure_reason": None,
    }


# =========================================================
# Graph Construction
# =========================================================


workflow = StateGraph(AgentState)

workflow.add_node(
    "infrastructure_error",
    record_infrastructure_error,
)

workflow.add_edge(
    "infrastructure_error",
    END,
)
workflow.add_node(
    "agent",
    call_model,
)

workflow.add_node(
    "tools",
    tool_node,
)

workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent",
    route_after_agent,
    {
        "agent": "agent",
        "tools": "tools",
        "end": END,
    },
)

workflow.add_conditional_edges(
    "tools",
    route_after_tools,
    {
        "agent": "agent",
        "infrastructure_error": "infrastructure_error",
        "end": END,
    },
)

clear_agent = workflow.compile()
