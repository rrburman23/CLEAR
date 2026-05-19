from src.agent.logic import clear_agent

def main():
    print("Initializing CLEAR Agent...")

    # Define the starting memory for the agent
    initial_state = {
        "task": "Write a Python function to add two numbers, and assert that 5 + 5 = 10.",
        "code": "",
        "error": "",
        "iterations": 0,
        "max_iterations": 3,
        "success": False,
    }

    # Invoke the LangGraph state machine
    final_state = clear_agent.invoke(initial_state) # pyright: ignore[reportArgumentType]

    print("\n=== FINAL RESULT ===")
    print(f"Total Iterations: {final_state['iterations']}")
    print(f"Success Status: {final_state['success']}")
    print("Final Healed Code:")
    print(final_state["code"])


if __name__ == "__main__":
    main()
