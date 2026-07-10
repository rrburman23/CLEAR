"""
CLEAR Agent Logic Module

Implements the LangGraph ReAct repair loop.

Architecture:

    Human
      |
      v
    CLEAR Agent
      |
      v
 run_repair_attempt()
      |
      v
 Docker Sandbox
      |
      v
 Test Result
      |
      v
    CLEAR Agent
      |
      v
 Verified Repair

The LLM never executes code directly.
All execution occurs inside SandboxManager.
"""

import os
import sys
import json
import codecs

from typing import Annotated, Sequence

from typing_extensions import TypedDict

from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
)

from langchain_ollama import ChatOllama

from src.tools.agent_tools import run_repair_attempt

from src.utils.config import OLLAMA_BASE_URL, MODEL_NAME, USE_REAL_LLM
from src.utils.parsers import extract_json


# ==========================================================
# Environment
# ==========================================================

load_dotenv()


# ==========================================================
# System Prompt
# ==========================================================

SYSTEM_PROMPT = """
You are CLEAR, an autonomous Python repair agent.

Your task:

Repair the broken target.py program.

You have exactly one tool:

run_repair_attempt(
    code,
    test_suite
)

Rules:

- code MUST contain ONLY the repaired target.py source (plain Python, no JSON, no markdown).
- test_suite MUST be passed through UNCHANGED, exactly as given to you.
- Never wrap code or test_suite in markdown fences.
- Never put implementation code inside test_suite.
- Never explain before a tool call.

Workflow:

1. Analyse the bug.
2. Call run_repair_attempt with the repaired code and the unchanged test_suite.
3. Read the execution result.
4. If it failed: fix the code and retry.
5. If it succeeded, reply with exactly:

Repair complete.
"""


# ==========================================================
# State
# ==========================================================


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


# ==========================================================
# Tools
# ==========================================================

TOOLS = [run_repair_attempt]
tool_node = ToolNode(TOOLS)


# ==========================================================
# LLM
# ==========================================================

SUPPORTED_TOOL_MODELS = ["qwen2.5", "llama3.1", "mistral"]

SUPPORTS_NATIVE_TOOLS = any(x in MODEL_NAME.lower() for x in SUPPORTED_TOOL_MODELS)


if USE_REAL_LLM:
    base_llm = ChatOllama(
        model=MODEL_NAME,
        base_url=OLLAMA_BASE_URL,
        temperature=0,
    )

    llm_engine = base_llm.bind_tools(TOOLS) if SUPPORTS_NATIVE_TOOLS else base_llm

else:

    class MockLLM:
        def invoke(self, messages):
            return AIMessage(content="Repair complete.")

    llm_engine = MockLLM()


# ==========================================================
# Tool-call payload normalisation
# ==========================================================


def _unwrap_value(value):
    """
    Small models sometimes double-wrap a string argument as
    {"type": "string", "value": "..."}. Collapse that to the inner string.
    """
    if isinstance(value, dict):
        if "value" in value and isinstance(value["value"], str):
            return value["value"]
        # Occasionally {"code": "..."} nested one level deeper.
        for key in ("code", "source", "text"):
            if key in value and isinstance(value[key], str):
                return value[key]
    return value


def _decode_escapes(value):
    """
    When a JSON payload is reconstructed from text, its string values can
    contain literal backslash-n sequences instead of real newlines, which
    the sandbox then fails to parse. Decode those escapes, but only when the
    string clearly contains them (avoid corrupting already-correct code).
    """
    if not isinstance(value, str):
        return value
    if "\\n" in value or "\\t" in value or '\\"' in value:
        try:
            return codecs.decode(value, "unicode_escape")
        except Exception:
            return value
    return value


def normalise_args(args: dict) -> dict:
    """
    Clean a tool-call argument dict so the sandbox receives valid raw Python.
    Applies unwrapping and escape-decoding to both code and test_suite.
    """
    if not isinstance(args, dict):
        return args

    cleaned = dict(args)
    for key in ("code", "test_suite"):
        if key in cleaned:
            cleaned[key] = _decode_escapes(_unwrap_value(cleaned[key]))
    return cleaned


# ==========================================================
# Agent Node
# ==========================================================


def call_model(state: AgentState):
    messages = list(state["messages"])

    if not messages or not isinstance(messages[0], SystemMessage):
        messages.insert(0, SystemMessage(content=SYSTEM_PROMPT))

    response = llm_engine.invoke(messages)

    # ----- Native tool calls: normalise their args in place -----
    if getattr(response, "tool_calls", None):
        fixed_calls = []
        for call in response.tool_calls:
            call = dict(call)
            call["args"] = normalise_args(call.get("args", {}))
            fixed_calls.append(call)
        response = AIMessage(content=response.content, tool_calls=fixed_calls)

    # ----- JSON polyfill: reconstruct a tool call from text -----
    else:
        payload = extract_json(str(response.content))
        if payload:
            args = payload.get("arguments", payload.get("args", payload))
            args = normalise_args(args if isinstance(args, dict) else {})
            if "code" in args:
                response = AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "run_repair_attempt",
                            "args": args,
                            "id": "json-tool",
                        }
                    ],
                )

    if os.getenv("DEBUG"):
        print(
            "DEBUG TOOL CALLS:", getattr(response, "tool_calls", None), file=sys.stderr
        )

    return {"messages": [response]}


# ==========================================================
# Routing
# ==========================================================


def should_continue(state):
    """Graph router. Success is defined by a verified ToolMessage."""
    last = state["messages"][-1]

    if isinstance(last, HumanMessage):
        return "agent"

    if isinstance(last, AIMessage):
        if getattr(last, "tool_calls", None):
            return "tools"

        content = str(getattr(last, "content", "")).lower()
        # Only "repair complete" ends the loop. Do NOT match "success" here:
        # the test suite itself may print SUCCESS.
        if "repair complete" in content:
            return "end"

        return "agent"

    if isinstance(last, ToolMessage):
        # Terminate as soon as the oracle confirms a pass, regardless of how
        # the model chooses to format its closing message afterwards.
        #if "SUCCESS: All tests pass" in str(last.content):
        #    return "end"
        return "agent"

    return "agent"


# ==========================================================
# Graph Construction
# ==========================================================

workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent",
    should_continue,
    {"tools": "tools", "agent": "agent", "end": END},
)

# After a tool runs, route through the router so a verified pass can end the
# loop immediately (instead of always bouncing back to the agent).
workflow.add_conditional_edges(
    "tools",
    should_continue,
    {"agent": "agent", "end": END},
)

workflow.add_edge("tools", "agent")

clear_agent = workflow.compile()
