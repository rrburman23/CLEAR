"""
Logic module for the CLEAR agent state machine.
Implements a production-grade message-based ReAct loop with native tool binding.
"""

from typing import Annotated, Sequence
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.prebuilt import ToolNode

from src.tools.agent_tools import read_file, write_file, execute_test_suite


# 1. Define State with Message Tracking
class AgentState(TypedDict):
    """
    Represents the unified state tracker for the CLEAR framework.
    Utilizes add_messages to append new interactions to the historical sequence.
    """

    messages: Annotated[Sequence[BaseMessage], add_messages]


# 2. Gather and Bind Tools
tools = [read_file, write_file, execute_test_suite]
tool_node = ToolNode(tools)


# --- MOCK LLM FOR INTEGRATION TESTING ---
class MockLLM:
    """Simulates an LLM producing tool calls and messages based on history."""

    def __init__(self):
        self.call_count = 0

    def __call__(self, state: AgentState) -> dict:
        self.call_count += 1
        history = state["messages"]

        # Determine the agent state based on the last message in history
        last_message = history[-1] if history else None

        # Loop Cycle 1: Agent decides to read the file to locate the bug
        if self.call_count == 1:
            return {
                "role": "assistant",
                "content": "I need to inspect the workspace files to check for faults.",
                "tool_calls": [
                    {
                        "name": "read_file",
                        "args": {"filename": "math_ops.py"},
                        "id": "call_read_01",
                    }
                ],
            }

        # Loop Cycle 2: Agent analyzes file contents and triggers a test suite execution
        elif self.call_count == 2:
            return {
                "role": "assistant",
                "content": "I see the file. Let me execute the test suite to observe failures.",
                "tool_calls": [
                    {"name": "execute_test_suite", "args": {}, "id": "call_test_01"}
                ],
            }

        # Loop Cycle 3: Agent acts on test suite outcomes (terminates or addresses errors)
        else:
            return {
                "role": "assistant",
                "content": "The test suite confirms all modules are functioning optimally. Repair phase complete.",
                "tool_calls": [],
            }


# Instantiate the engine
llm_engine = MockLLM()


# 3. Define Graph Nodes
def call_model(state: AgentState):
    """Executes the core reasoning node using the message history."""
    response = llm_engine(state)

    # Cast raw mock output into LangChain-compatible message dict format
    from langchain_core.messages import AIMessage

    ai_msg = AIMessage(content=response["content"], tool_calls=response["tool_calls"])
    return {"messages": [ai_msg]}


def should_continue(state: AgentState):
    """Evaluates conditional routing thresholds based on the last model execution."""
    last_message = state["messages"][-1]

    # If the model didn't request any tools, it has arrived at its conclusion
    if not getattr(last_message, "tool_calls", None):
        return "end"

    # Otherwise, route processing directly to the tool execution block
    return "continue"


# 4. Synthesize the Directed Acyclic Graph (DAG)
workflow = StateGraph(AgentState)

# Define processing nodes
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

# Define operational paths
workflow.set_entry_point("agent")

# Set up conditional routing out of the agent node
workflow.add_conditional_edges(
    "agent", should_continue, {"continue": "tools", "end": END}
)

# Loop the tool outputs back into the reasoning core
workflow.add_edge("tools", "agent")

# Compile framework
clear_agent = workflow.compile()
