import argparse
import json
import os
import re
import sys
import time

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.errors import GraphRecursionError

from src.agent.logic import AgentState, clear_agent
from src.utils.terminal import success, failure


# =========================================================
# UTF-8 Terminal Configuration
# =========================================================

stdout_reconfig = getattr(sys.stdout, "reconfigure", None)

if callable(stdout_reconfig):
    stdout_reconfig(encoding="utf-8")


stderr_reconfig = getattr(sys.stderr, "reconfigure", None)

if callable(stderr_reconfig):
    stderr_reconfig(encoding="utf-8")


# =========================================================
# Utility Functions
# =========================================================


def print_result(
    status: str,
    benchmark: str,
    reason: str | None = None,
    execution_time: float | None = None,
):
    """
    Machine-readable output consumed by benchmark runner.
    """

    result = {
        "status": status,
        "benchmark": benchmark,
        "reason": reason,
        "time": execution_time,
    }

    print("\n=== CLEAR_RESULT ===")
    print(json.dumps(result))
    print("=== END_CLEAR_RESULT ===\n")


def extract_code_block(text: str) -> str:
    """
    Extract Python code from markdown block.
    """

    match = re.search(
        r"```python\n(.*?)\n```",
        text,
        re.DOTALL,
    )

    if match:
        return match.group(1).strip()

    return ""


def get_benchmark_name(path: str) -> str:
    """
    Extract benchmark identifier.

    Example:

    tests/benchmarks/logic/factorial/target.py

    returns:

    logic:factorial
    """

    parts = os.path.normpath(path).split(os.sep)

    try:
        index = parts.index("benchmarks")

        category = parts[index + 1]
        benchmark = parts[index + 2]

        return f"{category}:{benchmark}"

    except Exception:
        return "unknown"


# =========================================================
# Main Execution
# =========================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CLEAR: Closed-Loop Engine for Autonomous Repair"
    )

    parser.add_argument(
        "--code",
        required=True,
        help="Path to broken Python source file",
    )

    parser.add_argument(
        "--test",
        required=True,
        help="Path to validation test suite",
    )

    args = parser.parse_args()

    benchmark_name = get_benchmark_name(args.code)

    target_file = os.path.abspath(args.code)
    test_file = os.path.abspath(args.test)

    benchmark_dir = os.path.dirname(target_file)

    sys.path.insert(0, benchmark_dir)

    print("====================================================")
    print("Initializing CLEAR Hybrid Orchestrator...")
    print("====================================================\n")

    print(f"Benchmark: {benchmark_name}\n")

    failure_reason = None

    # =====================================================
    # Load Benchmark Files
    # =====================================================

    try:
        with open(target_file, "r", encoding="utf-8") as file_handle:
            broken_code = file_handle.read()

        with open(test_file, "r", encoding="utf-8") as file_handle:
            test_suite = file_handle.read()

    except FileNotFoundError as exc:
        failure_reason = f"Missing file: {exc.filename}"

        failure(f"REPAIR_FAILED | Benchmark={benchmark_name} | Reason={failure_reason}")

        print_result(
            "FAILED",
            benchmark_name,
            failure_reason,
        )

        sys.exit(1)

    # =====================================================
    # Agent Prompt
    # =====================================================

    instruction = f"""
You are operating as an Atomic Logic Engine.

Current broken source code:

```python
{broken_code}
```

Validation test suite:

```python
{test_suite}
```

YOUR DIRECTIVE:

Use the run_repair_attempt tool.

The tool will:

modify the candidate code
execute the validation tests
verify correctness

Continue iterating until:

SUCCESS: All tests pass.

After successful verification:

output the final repaired Python code
place it inside a python markdown block

End your response with:

Repair complete.
"""

    initial_input: AgentState = {"messages": [HumanMessage(content=instruction)]}

    config: RunnableConfig = {"recursion_limit": 15}

    print("[WAIT] Agent deployed. Streaming execution logs live...\n")

    start_time = time.time()

    final_state = None

    # =====================================================
    # Agent Execution
    # =====================================================

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
                    print("👤 Human: (System Instruction Injected)")
                else:
                    print(f"👤 Human: {content_preview}")

            elif role == "AI":
                print(f"🧠 AI: {content_preview}")

                if getattr(last_message, "tool_calls", None):
                    tool_name = last_message.tool_calls[0]["name"]

                    print(f"   ⚙️ Tool Requested: {tool_name}")

            elif role == "Tool":
                print(f"🛠️ Tool: {content_preview}")

            final_state = event

    except GraphRecursionError:
        failure_reason = "Graph recursion limit reached"

    except Exception as exc:
        failure_reason = f"Execution error: {exc}"

    execution_time = time.time() - start_time

    print(f"\nTime to Resolution: {execution_time:.2f}s")

    print("====================================================\n")

    # =====================================================
    # Final Validation
    # =====================================================

    if final_state:
        last_message_text = final_state["messages"][-1].content

        healed_code = extract_code_block(last_message_text)

        if healed_code:
            success(f"REPAIR_SUCCESS | Benchmark={benchmark_name}")

            with open(target_file, "w", encoding="utf-8") as file_handle:
                file_handle.write(healed_code)

            success(f"Successfully overwritten {target_file}")

            print_result(
                status="SUCCESS",
                benchmark=benchmark_name,
                execution_time=execution_time,
            )

        else:
            failure_reason = "No repaired code returned"

            failure(
                f"REPAIR_FAILED | Benchmark={benchmark_name} | Reason={failure_reason}"
            )

            print("Final Agent Output:")
            print(last_message_text)

            print_result(
                status="FAILED",
                benchmark=benchmark_name,
                reason=failure_reason,
                execution_time=execution_time,
            )

    else:
        if failure_reason is None:
            failure_reason = "No final agent state returned"

        failure(f"REPAIR_FAILED | Benchmark={benchmark_name} | Reason={failure_reason}")

        print_result(
            status="FAILED",
            benchmark=benchmark_name,
            reason=failure_reason,
            execution_time=execution_time,
        )


if __name__ == "__main__":
    main()
