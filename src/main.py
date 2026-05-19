"""
Primary execution entry point for the CLEAR evaluation framework.
"""

from langchain_core.messages import HumanMessage
from src.agent.logic import clear_agent


def main():
    print("====================================================")
    print("Initializing Message-Driven CLEAR State Machine...")
    print("====================================================\n")

    # Seed the graph with an initial system request in message format
    initial_input = {
        "messages": [
            HumanMessage(
                content="Audit the workspace code for faults and fix any test failures."
            )
        ]
    }

    # Execute State Graph Trace
    config = {"recursion_limit": 10}
    final_output = clear_agent.invoke(initial_input, config=config)

    print("\n================== GRAPH COMPLETE ==================")
    print(f"Total Logged Message Transitions: {len(final_output['messages'])}")
    print("\nExecution History Log:")

    for i, msg in enumerate(final_output["messages"]):
        role = msg.__class__.__name__.replace("Message", "")
        print(f"[{i}] {role}: {msg.content}")
        if getattr(msg, "tool_calls", None):
            print(f"    Requested Tools: {msg.tool_calls}")
    print("====================================================")


if __name__ == "__main__":
    main()
