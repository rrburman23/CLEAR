# src/agent/routing.py
"""
CLEAR LangGraph Conditional Routing Logic

Determines the deterministic transitions between the Agent Node, the Tool Node,
and Graph Termination. Centralizes validation checks to ensure unverified
code is never recorded as a final success.
"""

from langchain_core.messages import AIMessage, ToolMessage

from src.agent.candidate import parse_tool_payload
from src.agent.state import AgentState


def route_after_agent(state: AgentState) -> str:
    """
    Evaluates the immediate output of the LLM generation cycle.
    Directs graph to execute tools, or halts upon systemic failure.
    """
    if state.get("terminal_failure"):
        return "end"

    last_message = state["messages"][-1]

    if isinstance(last_message, AIMessage):
        if getattr(last_message, "tool_calls", None):
            return "tools"

    return "agent"


def route_after_tools(state: AgentState) -> str:
    """
    Intercepts and interprets the raw execution response from the Docker container.
    Guarantees the framework only terminates if the execution explicitly passed
    all validation assertions.
    """
    last_message = state["messages"][-1]

    if not isinstance(last_message, ToolMessage):
        return "agent"

    payload = parse_tool_payload(last_message)

    if (
        payload
        and payload.get("status") == "SUCCESS"
        and isinstance(payload.get("code"), str)
        and payload["code"].strip()
    ):
        return "end"

    return "agent"
