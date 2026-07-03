import argparse
import os
import re
import sys
import time

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.errors import GraphRecursionError

from src.agent.logic import AgentState, clear_agent


def extract_code_block(text: str) -> str:
    """Extract Python code from a markdown block in the AI response."""
    match = re.search(r"```python\n(.*?)\n```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CLEAR: Closed-Loop Engine for Autonomous Repair"
    )
    parser.add_argument(
        "--code", required=True, help="Path to the broken Python source file"
    )
    parser.add_argument(
        "--test", required=True, help="Path to the atomic test suite file"
    )
    args = parser.parse_args()

    print("====================================================")
    print("Initializing CLEAR Hybrid Orchestrator...")
    print("====================================================\n")

    target_file = os.path.abspath(args.code)
    test_file = os.path.abspath(args.test)

    try:
        with open(target_file, "r", encoding="utf-8") as file_handle:
            broken_code = file_handle.read()
        with open(test_file, "r", encoding="utf-8") as file_handle:
            test_suite = file_handle.read()
    except FileNotFoundError as exc:
        print(f"❌ Error finding files: {exc}")
        print(
            "Please ensure you provided the correct paths to the code and test files."
        )
        sys.exit(1)

    instruction = f"""
You are operating as an Atomic Logic Engine.

Here is the current broken source code:
```python
{broken_code}
```

Here is the validation test suite:
```python
{test_suite}
```

YOUR DIRECTIVE:
- Use the run_repair_attempt tool to test modifications to the source code.
- Iterate until the tool returns a SUCCESS message indicating all tests pass.
- Once successful, you MUST output the final corrected code inside a python markdown block.
- Conclude your response with the exact phrase: "Repair complete."
"""

    initial_input: AgentState = {"messages": [HumanMessage(content=instruction)]}
    config: RunnableConfig = {"recursion_limit": 15}
    print("⏳ Agent deployed. Streaming execution logs live...\n")
    start_time = time.time()
    final_state = None

    try:
        for event in clear_agent.stream(
            initial_input,
            config=config,
            stream_mode="values",
        ):
            last_message = event["messages"][-1]
            role = last_message.__class__.__name__.replace("Message", "")
            content_preview = str(last_message.content).replace("\n", " ")
            if len(content_preview) > 130:
                content_preview = content_preview[:130] + "..."

            if role == "Human":
                if "Atomic Logic Engine" in str(last_message.content):
                    print(f"👤 {role}: (System Instruction & File State Injected)")
                else:
                    print(f"👤 {role} (Feedback): {content_preview}")
            elif role == "AI":
                print(f"🧠 {role}: {content_preview}")
                if getattr(last_message, "tool_calls", None):
                    tool_name = last_message.tool_calls[0]["name"]
                    print(f"   ⚙️ Tool Requested: {tool_name}")
            elif role == "Tool":
                print(f"🛠️ {role}: {content_preview}")

            final_state = event
    except GraphRecursionError:
        print("\n❌ GRAPH RECURSION LIMIT REACHED: The agent entered an infinite loop.")

    execution_time = time.time() - start_time
    print(f"\n⏱️ Time to Resolution: {execution_time:.2f} seconds")
    print("====================================================\n")

    if final_state:
        last_message_text = final_state["messages"][-1].content
        healed_code = extract_code_block(last_message_text)

        if "repair complete" in str(last_message_text).lower() and healed_code:
            print("✅ Repair Verified. Applying healed code to workspace...")
            with open(target_file, "w", encoding="utf-8") as file_handle:
                file_handle.write(healed_code)
            print(f"✅ Successfully overwritten {target_file}")
        else:
            print("⚠️ Agent terminated without a verified fix.")
            print("Final Agent Output:")
            print(last_message_text)


if __name__ == "__main__":
    main()
