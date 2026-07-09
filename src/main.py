"""
CLEAR: Closed-Loop Engine for Autonomous Repair
Main Orchestrator Node

This module serves as the primary entry point for a single repair task.
It instantiates the ReAct graph, injects the system prompts and file states,
and streams the interaction.

Academic Contribution:
Implements a comprehensive "Failure Taxonomy" tracker. Rather than a binary
pass/fail, this orchestrator diagnoses *why* an LLM failed (e.g., Infinite Loop,
Syntax Error, Formatting Error), enabling granular empirical analysis of LLM
reasoning constraints.
"""

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
from src.utils.terminal import success, failure, info, warning
from src.utils.parsers import extract_code_block
from src.utils.diff import generate_patch


# =========================================================
# UTF-8 Terminal Configuration
# =========================================================
# Forces standard output to UTF-8 to prevent 'charmap'
# codec crashes when rendering emojis or complex code tokens
# on Windows environments.

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
    Inter-Process Communication (IPC) Emitter.
    Outputs a strict JSON block that the parent benchmark runner captures
    and parses to build the final performance matrix and failure taxonomy.
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


def get_benchmark_name(path: str) -> str:
    """
    Extracts the unique benchmark identifier from its absolute path.
    Example: tests/benchmarks/logic/factorial/target.py -> logic:factorial
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
# Main Execution Node
# =========================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CLEAR: Closed-Loop Engine for Autonomous Repair"
    )
    parser.add_argument(
        "--code", required=True, help="Path to broken Python source file"
    )
    parser.add_argument("--test", required=True, help="Path to validation test suite")
    args = parser.parse_args()

    benchmark_name = get_benchmark_name(args.code)
    target_file = os.path.abspath(args.code)
    test_file = os.path.abspath(args.test)

    # Ensure local module imports work correctly for the tests
    benchmark_dir = os.path.dirname(target_file)
    sys.path.insert(0, benchmark_dir)

    info("====================================================")
    info(f"Initializing CLEAR Hybrid Orchestrator for: {benchmark_name}")
    info("====================================================\n")

    failure_reason = "Unknown Execution Failure"
    is_recursion_error = False

    # =====================================================
    # 1. Load Benchmark Files
    # =====================================================
    try:
        with open(target_file, "r", encoding="utf-8") as file_handle:
            broken_code = file_handle.read()

        with open(test_file, "r", encoding="utf-8") as file_handle:
            test_suite = file_handle.read()

    except FileNotFoundError as exc:
        failure_reason = f"Missing file environment error: {exc.filename}"
        failure(f"REPAIR_FAILED | Benchmark={benchmark_name} | Reason={failure_reason}")
        print_result("FAILED", benchmark_name, failure_reason)
        sys.exit(1)

    # =====================================================
    # 2. Agent Prompt Construction
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

    The tool will execute the tests inside a sandbox.

    Continue iterating until the tool returns: SUCCESS: All tests pass.

    Once successful, output the final repaired Python code inside a python markdown block.

    End your response with exactly: Repair complete.
"""

    initial_input: AgentState = {"messages": [HumanMessage(content=instruction)]}

    # Cap recursions at 15 to prevent infinite loops causing cost/time overruns
    config: RunnableConfig = {"recursion_limit": 15}

    print("[WAIT] Agent deployed. Streaming execution logs live...\n")
    start_time = time.time()
    final_state = None

    # =====================================================
    # 3. Agent Execution & Telemetry Streaming
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

            # Standard prints used here instead of loggers to keep
            # the live terminal UI clean and untracked in aggregate logs
            if role == "Human":
                if "Atomic Logic Engine" in str(last_message.content):
                    print("👤 Human: (System Instruction & Code Injected)")
                else:
                    print(f"👤 Human (Feedback): {content_preview}")
            elif role == "AI":
                print(f"🧠 AI: {content_preview}")
                if getattr(last_message, "tool_calls", None):
                    tool_name = last_message.tool_calls[0]["name"]
                    print(f"   ⚙️ Tool Requested: {tool_name}")
            elif role == "Tool":
                print(f"🛠️ Tool: {content_preview}")

                # --- TELEMETRY: Categorize Tool Failures in Real-Time ---
                if (
                    "SyntaxError" in content_preview
                    or "IndentationError" in content_preview
                ):
                    failure_reason = "Syntax / Execution error (Malformed Code)"
                elif (
                    "FAILURE" in content_preview or "AssertionError" in content_preview
                ):
                    failure_reason = "Sandbox verification failure (Logic Error)"

            final_state = event

    except GraphRecursionError:
        warning("\n❌ GRAPH RECURSION LIMIT REACHED: Agent caught in infinite loop.")
        is_recursion_error = True
        failure_reason = "Infinite Loop (Recursion Limit)"

    except Exception as exc:
        warning(f"\n❌ UNEXPECTED SYSTEM EXCEPTION: {exc}")
        failure_reason = f"System Crash: {exc}"

    execution_time = time.time() - start_time
    print(f"\nTime to Resolution: {execution_time:.2f}s")
    print("====================================================\n")

    # =====================================================
    # 4. Final Validation & Taxonomy Classification
    # =====================================================

    status = "FAILED"

    if final_state and not is_recursion_error:
        last_message_text = str(final_state["messages"][-1].content)
        healed_code = extract_code_block(last_message_text)

        # Check if the LLM outputted the required terminal string
        if "repair complete" in last_message_text.lower():
            if healed_code:
                # Absolute Success State
                status = "SUCCESS"
                failure_reason = None
                success(f"REPAIR_SUCCESS | Benchmark={benchmark_name}")
                
                # Generate a diff patch for the repaired code 
                patch = generate_patch(
                    broken_code, healed_code, os.path.basename(target_file)
                )
                info("\n--- APPLIED PATCH ---")
                print(patch)
                info("---------------------\n")

                # Commit the healed code back to the disk
                with open(target_file, "w", encoding="utf-8") as file_handle:
                    file_handle.write(healed_code)
                success(f"Successfully overwritten {target_file}")
            else:
                failure_reason = (
                    "Final response formatting failure (Missing Markdown Code Block)"
                )
                failure(f"REPAIR_FAILED | Reason={failure_reason}")
                print("\nFinal Agent Output:\n", last_message_text)
        else:
            # The LLM stopped outputting tool calls but forgot to print the completion string
            failure_reason = (
                "Final response formatting failure (Missing 'Repair complete' phrase)"
            )
            failure(f"REPAIR_FAILED | Reason={failure_reason}")
            print("\nFinal Agent Output:\n", last_message_text)

    elif is_recursion_error:
        failure(f"REPAIR_FAILED | Benchmark={benchmark_name} | Reason={failure_reason}")

    else:
        if failure_reason == "Unknown Execution Failure":
            failure_reason = "No final agent state returned (Catastrophic Crash)"
        failure(f"REPAIR_FAILED | Benchmark={benchmark_name} | Reason={failure_reason}")

    # Emit the structured IPC JSON
    print_result(
        status=status,
        benchmark=benchmark_name,
        reason=failure_reason,
        execution_time=execution_time,
    )


if __name__ == "__main__":
    main()
