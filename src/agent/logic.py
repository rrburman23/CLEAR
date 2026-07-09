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
import re
import json
import uuid
import sys

from typing import Any, Annotated, Sequence

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

- code MUST contain ONLY repaired target.py.
- test_suite MUST remain unchanged.
- Never put implementation code inside test_suite.
- Never modify tests.
- Never use markdown.
- Never explain before tool calls.

Workflow:

1. Analyse the bug.
2. Call run_repair_attempt.
3. Read the execution result.
4. If failed:
      fix the code
      retry.
5. If successful:

Reply exactly:

Repair complete.

"""


# ==========================================================
# State
# ==========================================================


class AgentState(TypedDict):

    messages: Annotated[
            Sequence[BaseMessage],
            add_messages
        ]


# ==========================================================
# Tools
# ==========================================================


TOOLS = [
    run_repair_attempt
]


tool_node = ToolNode(TOOLS)



# ==========================================================
# LLM
# ==========================================================


SUPPORTED_TOOL_MODELS = [
    "qwen2.5",
    "llama3.1",
    "mistral"
]


SUPPORTS_NATIVE_TOOLS = any(
    x in MODEL_NAME.lower()
    for x in SUPPORTED_TOOL_MODELS
)



if USE_REAL_LLM:

    base_llm = ChatOllama(
        model=MODEL_NAME,
        base_url=OLLAMA_BASE_URL,
        temperature=0
    )


    if SUPPORTS_NATIVE_TOOLS:

        llm_engine = base_llm.bind_tools(
            TOOLS
        )

    else:

        llm_engine = base_llm


else:


    class MockLLM:

        def invoke(self, messages):

            return AIMessage(
                content="Repair complete."
            )


    llm_engine = MockLLM()





# ==========================================================
# Tool Call Normalisation
# ==========================================================


def normalise_call(call):

    if isinstance(call, dict):

        return (
            call.get("name"),
            call.get(
                "args",
                call.get(
                    "arguments",
                    {}
                )
            )
        )


    return (
        getattr(call,"name",""),
        getattr(call,"args",{})
    )



# ==========================================================
# Agent Node
# ==========================================================


def call_model(state:AgentState):


    messages = list(
        state["messages"]
    )


    if not messages or not isinstance(
        messages[0],
        SystemMessage
    ):

        messages.insert(
            0,
            SystemMessage(
                content=SYSTEM_PROMPT
            )
        )


    response = llm_engine.invoke(
        messages
    )


    # --------------------------------------
    # JSON compatibility layer
    # --------------------------------------

    # If the model didn't trigger native tools, ALWAYS check the text for a JSON block
    if not getattr(response, "tool_calls", None):
        payload = extract_json(str(response.content))
        if payload:
            args = payload.get("arguments", payload.get("args", {}))
            response = AIMessage(
                content="",
                tool_calls=[
                    {"name": "run_repair_attempt", "args": args, "id": "json-tool"}
                ],
            )
    

    if os.getenv("DEBUG"):

        print(
            "DEBUG TOOL CALLS:",
            response.tool_calls,
            file=sys.stderr
        )


    return {
        "messages":
            [response]
    }



# ==========================================================
# Routing
# ==========================================================


def should_continue(state):
    """
    Graph Router
    """
    last = state["messages"][-1]

    if isinstance(last, HumanMessage):
        return "agent"

    # If the AI generated a tool call, route to the tool
    if isinstance(last, AIMessage):
        if getattr(last, "tool_calls", None):
            return "tools"

        content = str(getattr(last, "content", "")).lower()
        # ONLY check for "repair complete".
        # DO NOT check for "success" because the test suite contains print("SUCCESS")!
        if "repair complete" in content:
            return "end"

        return "agent"

    # If the tool just ran, ALWAYS route back to the agent so it can read the result
    if isinstance(last, ToolMessage):
        return "agent"

    return "agent"



# ==========================================================
# Graph Construction
# ==========================================================


workflow = StateGraph(
    AgentState
)


workflow.add_node(
    "agent",
    call_model
)


workflow.add_node(
    "tools",
    tool_node
)



workflow.set_entry_point(
    "agent"
)



workflow.add_conditional_edges(

    "agent",

    should_continue,

    {

        "tools":
            "tools",

        "agent":
            "agent",

        "end":
            END

    }

)



workflow.add_edge(
    "tools",
    "agent"
)



clear_agent = workflow.compile()