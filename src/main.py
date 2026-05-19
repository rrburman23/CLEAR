import time
import threading
import sys
from langchain_core.messages import HumanMessage
from src.agent.logic import clear_agent


class LiveTimer:
    """A background thread that prints a live updating clock to the terminal."""

    def __init__(self):
        self.running = False
        self.start_time = 0

    def run(self):
        while self.running:
            elapsed = time.time() - self.start_time
            # \r brings the cursor back to the start of the line so it overwrites itself
            sys.stdout.write(
                f"\r⏳ Agent deployed. Running for: {elapsed:.1f} seconds..."
            )
            sys.stdout.flush()
            time.sleep(0.1)

    def start(self):
        self.running = True
        self.start_time = time.time()
        # daemon=True ensures the thread dies when the main program finishes
        threading.Thread(target=self.run, daemon=True).start()

    def stop(self):
        self.running = False
        time.sleep(0.1)  # Give the thread a split second to finish its last loop
        sys.stdout.write("\n")  # Push to a new line so we don't overwrite the clock


def main():
    print("====================================================")
    print("Initializing Message-Driven CLEAR State Machine...")
    print("====================================================\n")

    initial_input = {
        "messages": [
            HumanMessage(
                content="Execute the test suite in the workspace. It contains multiple failures across different files. "
                "Read the failing files, implement the correct logic, and repeat this process until the entire "
                "test suite passes with 100% success."
            )
        ]
    }

    config = {"recursion_limit": 25}

    # --- START LIVE CLOCK ---
    timer = LiveTimer()
    timer.start()

    # Store start time for the final summary calculation
    start_time = time.time()

    # Invoke the graph
    final_output = clear_agent.invoke(initial_input, config=config) # type: ignore

    # --- STOP LIVE CLOCK ---
    timer.stop()
    execution_time = time.time() - start_time

    print("\n================== GRAPH COMPLETE ==================")
    print(f"Total Logged Message Transitions: {len(final_output['messages'])}")
    print(f"Time to Resolution (TTR): {execution_time:.2f} seconds")
    print("\nExecution History Log:")

    for i, msg in enumerate(final_output["messages"]):
        role = msg.__class__.__name__.replace("Message", "")
        content_preview = (
            msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
        )
        print(f"[{i}] {role}: {content_preview.strip()}")
        if getattr(msg, "tool_calls", None):
            print(f"    Requested Tools: {msg.tool_calls}")
    print("====================================================")


if __name__ == "__main__":
    main()
