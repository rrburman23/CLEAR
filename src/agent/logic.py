"""
Logic module for the CLEAR agent state machine.
Implements a message-based ReAct loop with native tool binding,
system prompt injection, and forced-action logic for local SLMs via Ollama.
"""

import os
from dotenv import load_dotenv
from typing import Annotated, Sequence
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import SystemMessage, BaseMessage, AIMessage, HumanMessage
from langgraph.prebuilt import ToolNode
from langchain_ollama import ChatOllama

# Import the custom tools we built for the CLEAR framework
from src.tools.agent_tools import (
    read_file,
    write_file,
    execute_test_suite,
    run_repair_attempt,
)

# Load environment configuration
load_dotenv()

# --- MASTER SYSTEM PROMPT ---
SYSTEM_PROMPT = """
You are CLEAR, an autonomous, senior software engineering agent.
Your primary objective is to debug, heal, and verify Python code.

You have access to a secure, isolated workspace and the following tools:
1. `read_file(filename: str)`: Inspect the contents of a file.
2. `write_file(filename: str, content: str)`: Overwrite a file with corrected code.
3. `execute_test_suite()`: Run the test suite to verify if the code works.

CRITICAL RULES FOR TOOL CALLING:
- NEVER write JSON tool calls manually in your text response. You MUST use the official tool calling API.
- NEVER guess the code. ALWAYS call `execute_test_suite` first, read the error traceback, and then call `read_file` on the EXACT filename mentioned in the error.
- DO NOT invent file paths. If the error says `test_math_ops.py`, the filename is just `test_math_ops.py`.
- ALWAYS verify your fixes by running `execute_test_suite` again.
- ABORT IF YOU TYPE JSON: You are physically incapable of executing tools by typing JSON dictionaries in your chat response. You MUST use the underlying API binding. Outputting raw JSON like {"name": "read_file"} will cause a fatal system crash.

CRITICAL RULE: 
- Before declaring "Repair complete", you MUST confirm that the test suite reports "0 failed".
- If the test suite shows multiple failures, you MUST address each one iteratively. 
- NEVER GENERATE CODE FROM MEMORY. If you see a file mentioned in an error, 
  you are strictly forbidden from writing code for it until you have called `read_file`. 

EXAMPLE WORKFLOW:
1. You call `execute_test_suite`.
2. Tool returns an error in `math_ops.py`.
3. You call `read_file` with argument filename="math_ops.py".
4. You analyze the code, then call `write_file` with the corrected code.
5. You call `execute_test_suite` again to verify.
6. Once the test passes, you output: "Repair complete."
"""

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
USE_REAL_LLM = os.getenv("USE_REAL_LLM", "False").lower() == "true"


# 1. Define State with Message Tracking
class AgentState(TypedDict):
    """
    Represents the unified state tracker for the CLEAR framework.
    Utilizes add_messages to append new interactions to the historical sequence.
    """

    messages: Annotated[Sequence[BaseMessage], add_messages]


# 2. Gather and Bind Tools
tools = [read_file, write_file, execute_test_suite, run_repair_attempt]
tool_node = ToolNode(tools)


# 3. Initialize the Core Reasoning Engine
if USE_REAL_LLM:
    print(f"🔗 Connecting to Local Ollama at {OLLAMA_BASE_URL}...")
    llm_engine = ChatOllama(
        base_url=OLLAMA_BASE_URL, model="llama3.1", temperature=0.0
    ).bind_tools(tools)
else:
    print("⚠️ Using MockLLM (Real LLM disabled in .env)")

    class MockLLM:
        def __init__(self):
            self.call_count = 0

        def invoke(self, messages) -> AIMessage:
            self.call_count += 1
            if self.call_count == 1:
                return AIMessage(
                    content="Need to check files.",
                    tool_calls=[
                        {
                            "name": "read_file",
                            "args": {"filename": "math_ops.py"},
                            "id": "1",
                        }
                    ],
                )
            return AIMessage(content="Repair complete.")

    llm_engine = MockLLM()


# 4. Define Graph Nodes
def call_model(state: AgentState):
    """Executes the core reasoning node with forced action constraints."""
    messages = state["messages"]

    # Prepend System Prompt to ensure it is always in context
    if not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)

    response = llm_engine.invoke(messages)

    # FORCED ACTION: If model produces text only (no tools) and isn't finished,
    # force a reminder back to the model to maintain agentic momentum.
    response_content = getattr(response, "content", "")
    response_text = str(response_content).lower()
    if not response.tool_calls and "repair complete" not in response_text:
        reminder = HumanMessage(
            content="CRITICAL: You are in a reasoning loop but haven't called a tool. You must use a tool to progress."
        )
        return {"messages": [response, reminder]}

    return {"messages": [response]}


def should_continue(state: AgentState):
    """
    Routes the graph:
    - continue: To the ToolNode
    - end: Terminate the graph
    """
    last_message = state["messages"][-1]

    # If tools were requested, route to the tool node
    if getattr(last_message, "tool_calls", None):
        return "continue"

    # Termination logic
    content = getattr(last_message, "content", "")
    content_text = str(content).lower()
    if any(
        keyword in content_text for keyword in ["repair complete", "all tests pass"]
    ):
        return "end"

    # Otherwise loop back
    return "continue"


# 5. Synthesize the Directed Acyclic Graph (DAG)
workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent", should_continue, {"continue": "tools", "end": END}
)

workflow.add_edge("tools", "agent")

clear_agent = workflow.compile()
