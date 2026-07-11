# src/agent/logic.py
"""
CLEAR Central Orchestrator

The declarative backbone of the self-healing framework. Composes modules
from the `src/agent/` domain into a compiled LangGraph application.
This is the only module external systems (e.g., src.main) need to import.
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from src.agent.candidate import convert_text_response_to_tool_call, normalise_args
from src.agent.model_adapter import invoke_model
from src.agent.routing import route_after_agent, route_after_tools
from src.agent.state import AgentState
from src.tools.agent_tools import run_repair_attempt

# =========================================================
# Configuration
# =========================================================

MAX_INVALID_RESPONSES = 3
TOOLS = [run_repair_attempt]
tool_node = ToolNode(TOOLS)

# =========================================================
# Agent Node Definition
# =========================================================


def call_model(state: AgentState) -> dict[str, Any]:
    """
    The computational core of the repair loop. Generates code, enforces
    protocol constraints, applies fallbacks, and mutates the AgentState.
    """
    response, used_text_mode = invoke_model(state["messages"])
    canonical_test_suite = state["test_suite"]

    tool_calls = getattr(response, "tool_calls", None) or []

    # Path A: The model natively formatted a valid tool call
    if tool_calls and not used_text_mode:
        normalised_calls = []

        for index, tool_call in enumerate(tool_calls, start=1):
            arguments = normalise_args(tool_call.get("args", {}))
            candidate_code = arguments.get("code", "")

            if not candidate_code.strip():
                continue

            normalised_calls.append(
                {
                    "name": "run_repair_attempt",
                    "args": {
                        "code": candidate_code,
                        "test_suite": canonical_test_suite,
                    },
                    "id": tool_call.get("id", f"clear-native-call-{index}"),
                }
            )

        if normalised_calls:
            normalised_response = AIMessage(
                content=response.content,
                tool_calls=normalised_calls,
            )
            return {
                "messages": [normalised_response],
                "invalid_responses": 0,
                "terminal_failure": None,
            }

    # Path B: The model produced text, applying Candidate Polyfill Layer
    converted_response = convert_text_response_to_tool_call(
        response_text=str(response.content),
        canonical_test_suite=canonical_test_suite,
    )

    if converted_response is not None:
        return {
            "messages": [converted_response],
            "invalid_responses": 0,
            "terminal_failure": None,
        }

    # Path C: The model produced unparseable garbage; manage retry state
    invalid_responses = state.get("invalid_responses", 0) + 1

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
            "Markdown code block. Do not include explanations."
        )
    )

    return {
        "messages": [response, feedback],
        "invalid_responses": invalid_responses,
        "terminal_failure": None,
    }


# =========================================================
# Graph Compilation
# =========================================================

workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

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

# Exposed API for src.main.py execution
clear_agent = workflow.compile()
