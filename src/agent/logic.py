"""
Logic module for the CLEAR agent state machine.
Handles reasoning (generation) and action (execution) loops.
"""

from typing import TypedDict
from langgraph.graph import StateGraph, END
from src.core.sandbox import SandboxManager


# 1. Define the 'Memory' of our agent
class AgentState(TypedDict):
    """
    Represents the internal state of the CLEAR agent.
    """

    task: str  # The original bug or feature request
    code: str  # The current version of the code
    error: str  # The last error message from the sandbox
    iterations: int  # How many times we've tried to fix it
    max_iterations: int  # The limit before we give up
    success: bool  # Did it pass validation?


# 2. Initialize our Sandbox Guard
sandbox = SandboxManager()


def generator_node(state: AgentState):
    """The 'Reasoning' node: LLM analyzes the error and writes code."""
    print(f"--- ATTEMPT {state['iterations'] + 1} ---")

    # Construct a 'Closed-Loop' prompt
    prompt = f"Task: {state['task']}\n"
    if state["error"]:
        prompt += f"Previous error: {state['error']}\n"
        prompt += "Analyze the error above and provide a corrected Python script."
    else:
        prompt += "Write a Python script to solve this task."

    # TODO: This is where we call Ollama (DeepSeek-Coder)
    # For now, we will placeholder the LLM call
    new_code = "# LLM generated code goes here"

    return {"code": new_code, "iterations": state["iterations"] + 1}


def executor_node(state: AgentState):
    """The 'Action' node: Run the code in Docker and see what happens."""
    result = sandbox.run_code(state["code"])

    if result["status"] == "success":
        print("✅ Code Passed!")
        return {"success": True, "error": ""}
    else:
        print("❌ Code Failed. Capturing Traceback...")
        return {"success": False, "error": result["error"]}
    

def should_continue(state: AgentState):
    """Decision logic: Should we loop back or end?"""
    if state["success"] or state["iterations"] >= state["max_iterations"]:
        return "end"
    return "generate"


# 3. Build the Graph
workflow = StateGraph(AgentState)

# Add our nodes
workflow.add_node("generate", generator_node)
workflow.add_node("execute", executor_node)

# Define the flow
workflow.set_entry_point("generate")
workflow.add_edge("generate", "execute")

# Add the conditional 'Closed-Loop' edge
workflow.add_conditional_edges(
    "execute", should_continue, {"generate": "generate", "end": END}
)

# Compile the brain
clear_agent = workflow.compile()