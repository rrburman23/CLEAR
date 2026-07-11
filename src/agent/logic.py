"""
CLEAR Central Orchestrator

Composes the repair-agent modules into a compiled LangGraph application.

This module defines the model node and graph structure. External callers need
only import clear_agent from this module.
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from src.agent.candidate import (
    build_candidate_tracking_update,
    convert_text_response_to_tool_call,
    normalise_args,
)
from src.agent.model_adapter import (
    get_candidate_code,
    invoke_model,
)
from src.agent.routing import (
    route_after_agent,
    route_after_tools,
)
from src.agent.state import AgentState
from src.tools.agent_tools import run_repair_attempt


# =========================================================
# Configuration
# =========================================================

MAX_INVALID_RESPONSES = 3

TOOLS = [
    run_repair_attempt,
]

tool_node = ToolNode(TOOLS)


# =========================================================
# State Update Helpers
# =========================================================


def build_valid_candidate_update(
    *,
    state: AgentState,
    response: AIMessage,
) -> dict[str, Any]:
    """
    Build a graph state update for an executable repair candidate.

    Candidate tracking occurs only after the response has been converted into
    the exact tool call that will be routed to the sandbox.
    """

    state_update: dict[str, Any] = {
        "messages": [response],
        "invalid_responses": 0,
        "terminal_failure": None,
    }

    candidate_code = get_candidate_code(response)

    if candidate_code is not None:
        state_update.update(
            build_candidate_tracking_update(
                state=state,
                candidate_code=candidate_code,
            )
        )

    return state_update


# =========================================================
# Agent Node
# =========================================================


def call_model(
    state: AgentState,
) -> dict[str, Any]:
    """
    Generate one candidate repair.

    Processing order:

    1. Invoke the configured model.
    2. Accept and normalise a native tool call where available.
    3. Otherwise convert text output into a synthetic tool call.
    4. Track the resulting executable candidate.
    5. Request corrected formatting after invalid responses.
    """

    response, used_text_mode = invoke_model(state["messages"])

    canonical_test_suite = state["test_suite"]

    tool_calls = (
        getattr(
            response,
            "tool_calls",
            None,
        )
        or []
    )

    # =====================================================
    # Path A: Valid native tool call
    # =====================================================

    if tool_calls and not used_text_mode:
        normalised_calls: list[dict[str, Any]] = []

        for index, tool_call in enumerate(
            tool_calls,
            start=1,
        ):
            arguments = normalise_args(
                tool_call.get(
                    "args",
                    {},
                )
            )

            candidate_code = arguments.get(
                "code",
                "",
            )

            if not candidate_code.strip():
                continue

            normalised_calls.append(
                {
                    "name": "run_repair_attempt",
                    "args": {
                        "code": candidate_code,
                        "test_suite": canonical_test_suite,
                    },
                    "id": tool_call.get(
                        "id",
                        f"clear-native-call-{index}",
                    ),
                }
            )

            # One candidate is evaluated per graph iteration.
            break

        if normalised_calls:
            normalised_response = AIMessage(
                content=response.content,
                tool_calls=normalised_calls,
            )

            return build_valid_candidate_update(
                state=state,
                response=normalised_response,
            )

    # =====================================================
    # Path B: Text compatibility conversion
    # =====================================================

    converted_response = convert_text_response_to_tool_call(
        response_text=str(response.content),
        canonical_test_suite=canonical_test_suite,
    )

    if converted_response is not None:
        return build_valid_candidate_update(
            state=state,
            response=converted_response,
        )

    # =====================================================
    # Path C: Invalid model protocol response
    # =====================================================

    invalid_responses = (
        state.get(
            "invalid_responses",
            0,
        )
        + 1
    )

    if invalid_responses >= MAX_INVALID_RESPONSES:
        return {
            "messages": [response],
            "invalid_responses": invalid_responses,
            "terminal_failure": (
                "Model protocol failure: no executable repair payload "
                f"after {invalid_responses} responses"
            ),
        }

    feedback = HumanMessage(
        content=(
            "Your response could not be converted into a repair attempt. "
            "Return only the complete repaired target.py inside one Python "
            "Markdown code block. Do not include explanations, the test "
            "suite, or CLEAR framework code."
        )
    )

    return {
        "messages": [
            response,
            feedback,
        ],
        "invalid_responses": invalid_responses,
        "terminal_failure": None,
    }


# =========================================================
# Graph Compilation
# =========================================================

workflow = StateGraph(AgentState)

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
        "end": END,
    },
)


# Public compiled graph used by src.main.
clear_agent = workflow.compile()
