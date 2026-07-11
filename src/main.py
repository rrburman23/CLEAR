"""
CLEAR Single-Repair Orchestrator

Runs one autonomous repair task and emits a structured CLEAR_RESULT
record for run_benchmarks.py.

The repair is considered successful only when run_repair_attempt returns
a structured SUCCESS result containing the exact candidate code that
passed the sandbox validation suite.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from typing import Any, Sequence, cast

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    ToolMessage,
)
from langchain_core.runnables import RunnableConfig
from langgraph.errors import GraphRecursionError

from src.agent.logic import AgentState, clear_agent
from src.utils.diff import generate_patch
from src.utils.terminal import failure, info, success, warning


# =========================================================
# Configuration
# =========================================================

DEFAULT_RECURSION_LIMIT = 31
MESSAGE_PREVIEW_LIMIT = 150


# =========================================================
# Terminal Configuration
# =========================================================


def configure_logging() -> None:
    """
    Prevent duplicate fallback logging when src.main is run directly.

    run_benchmarks.py configures its own file logger. When main.py is run
    independently, NullHandler prevents messages such as:

        WARNING:root:FAILED: ...
    """
    root_logger = logging.getLogger()

    if not root_logger.handlers:
        root_logger.addHandler(logging.NullHandler())


def configure_utf8_stream(stream: Any) -> None:
    """
    Configure stdout or stderr to use UTF-8 where supported.
    """
    reconfigure = getattr(stream, "reconfigure", None)

    if callable(reconfigure):
        reconfigure(
            encoding="utf-8",
            errors="replace",
        )


configure_logging()
configure_utf8_stream(sys.stdout)
configure_utf8_stream(sys.stderr)


# =========================================================
# CLEAR_RESULT Output
# =========================================================


def print_result(
    *,
    status: str,
    benchmark: str,
    reason: str | None,
    execution_time: float,
    iterations: int,
    verified: bool,
) -> None:
    """
    Emit the structured result consumed by run_benchmarks.py.
    """
    result = {
        "status": status,
        "benchmark": benchmark,
        "reason": reason,
        "time": execution_time,
        "iterations": iterations,
        "verified": verified,
    }

    print("\n=== CLEAR_RESULT ===")
    print(
        json.dumps(
            result,
            ensure_ascii=False,
        )
    )
    print("=== END_CLEAR_RESULT ===\n")


# =========================================================
# Benchmark Identification
# =========================================================


def get_benchmark_name(path: str) -> str:
    """
    Extract a category:benchmark identifier from a benchmark path.

    Example:
        tests/benchmarks/logic/factorial/target.py

    becomes:
        logic:factorial
    """
    path_parts = os.path.normpath(path).split(os.sep)

    try:
        benchmark_index = path_parts.index("benchmarks")
        category = path_parts[benchmark_index + 1]
        benchmark = path_parts[benchmark_index + 2]
        return f"{category}:{benchmark}"

    except (ValueError, IndexError):
        parent_directory = os.path.basename(os.path.dirname(path))
        filename = os.path.basename(path)
        return f"{parent_directory}:{filename}"


# =========================================================
# File Utilities
# =========================================================


def read_text_file(path: str) -> str:
    """
    Read a UTF-8 text file.
    """
    with open(path, "r", encoding="utf-8") as file_handle:
        return file_handle.read()


# =========================================================
# Tool Result Parsing
# =========================================================


def parse_tool_payload(message: ToolMessage) -> dict[str, Any] | None:
    """
    Parse the structured JSON returned by run_repair_attempt.
    """
    try:
        payload = json.loads(str(message.content))
    except (json.JSONDecodeError, TypeError):
        return None

    if not isinstance(payload, dict):
        return None

    return payload


def find_successful_repair(
    messages: Sequence[BaseMessage],
) -> tuple[str | None, dict[str, Any] | None]:
    """
    Find the newest sandbox-verified repair candidate.
    """
    for message in reversed(messages):
        if not isinstance(message, ToolMessage):
            continue

        payload = parse_tool_payload(message)
        if not payload:
            continue

        candidate_code = payload.get("code")
        if (
            payload.get("status") == "SUCCESS"
            and isinstance(candidate_code, str)
            and candidate_code.strip()
        ):
            return candidate_code, payload

    return None, None


def find_latest_tool_failure(
    messages: Sequence[BaseMessage],
) -> dict[str, Any] | None:
    """
    Find the newest failed sandbox result.
    """
    for message in reversed(messages):
        if not isinstance(message, ToolMessage):
            continue

        payload = parse_tool_payload(message)
        if payload and payload.get("status") == "FAILURE":
            return payload

    return None


# =========================================================
# Repair Attempt Counting
# =========================================================

def count_repair_attempts(
    messages: Sequence[BaseMessage],
) -> int:
    """
    Count completed sandbox executions.

    ToolMessage objects represent repair attempts that were actually
    executed. Counting AI tool requests can overcount an unexecuted final
    request when the graph reaches its recursion limit.
    """

    attempts = 0

    for message in messages:
        if not isinstance(
            message,
            ToolMessage,
        ):
            continue

        # CLEAR currently exposes only one execution tool. Every ToolMessage
        # therefore represents one completed repair attempt.
        attempts += 1

    return attempts

# =========================================================
# Failure Classification
# =========================================================


def classify_tool_failure(payload: dict[str, Any] | None) -> str:
    """
    Convert sandbox feedback into a consistent failure category.
    """
    if not payload:
        return "No valid repair attempt generated"

    combined_feedback = " ".join(
        [
            str(payload.get("message", "")),
            str(payload.get("error", "")),
            str(payload.get("output", "")),
        ]
    ).lower()

    if "timeout" in combined_feedback:
        return "Sandbox timeout"

    if any(
        error_name in combined_feedback
        for error_name in ("syntaxerror", "indentationerror", "taberror")
    ):
        return "Malformed candidate code"

    if any(
        marker in combined_feedback
        for marker in (
            "assertionerror",
            "tests failed",
            "test failed",
            "did not pass",
            "verification failed",
        )
    ):
        return "Sandbox verification failure"

    if any(
        error_name in combined_feedback
        for error_name in ("modulenotfounderror", "importerror")
    ):
        return "Candidate import failure"

    if any(
        error_name in combined_feedback
        for error_name in (
            "typeerror",
            "valueerror",
            "keyerror",
            "indexerror",
            "attributeerror",
            "nameerror",
            "zerodivisionerror",
            "filenotfounderror",
            "jsondecodeerror",
        )
    ):
        return "Candidate runtime failure"

    if any(
        marker in combined_feedback
        for marker in ("docker", "container", "daemon")
    ):
        return "Sandbox infrastructure failure"

    explicit_error = payload.get("error")
    if isinstance(explicit_error, str) and explicit_error.strip():
        return "Candidate execution failure"

    return "Sandbox verification failure"


# =========================================================
# Prompt Construction
# =========================================================


def build_repair_instruction(
    broken_code: str,
    test_suite: str,
) -> str:
    """
    Construct the repair specification.

    Tool and framework implementation details are intentionally omitted
    because text-only models may incorrectly place them inside target.py.
    """

    return f"""
Repair the following Python program.

BROKEN TARGET.PY

```python
{broken_code}
```

VALIDATION TEST SUITE

```python
{test_suite}
```

REPAIR REQUIREMENTS

1. Produce a complete standalone replacement for target.py.
2. Preserve the intended public functions, classes and behaviour.
3. Do not modify, weaken, remove, replace or bypass the tests.
4. Do not include the test suite in the repaired source.
5. Do not import or reference CLEAR or its repair infrastructure.
6. Do not import run_repair_attempt, LangChain, LangGraph or Docker.
7. Use execution feedback to improve the program when a candidate fails.
8. Continue until the supplied tests pass.
""".strip()


# =========================================================
# Streaming Output
# =========================================================


def make_content_preview(content: Any, limit: int = MESSAGE_PREVIEW_LIMIT) -> str:
    """Convert message content into a short one-line preview."""
    preview = str(content).replace("\n", " ")

    if len(preview) > limit:
        return preview[:limit] + "..."

    return preview


def display_stream_message(message: BaseMessage) -> None:
    """Display one LangGraph message in the terminal."""
    preview = make_content_preview(message.content)

    if isinstance(message, HumanMessage):
        if "BROKEN TARGET.PY" in str(message.content):
            print("Human: (Repair specification and source injected)")
        else:
            print(f"Human: {preview}")
        return

    if isinstance(message, AIMessage):
        print(f"AI: {preview}")

        tool_calls = getattr(message, "tool_calls", None) or []
        for tool_call in tool_calls:
            print("   Tool Requested: " f"{tool_call.get('name', 'unknown')}")
        return

    if isinstance(message, ToolMessage):
        payload = parse_tool_payload(message)

        if payload:
            tool_status = payload.get("status", "UNKNOWN")
            tool_message = payload.get("message", "")
            print(f"Tool: {tool_status} | {tool_message}")
        else:
            print(f"Tool: {preview}")


# =========================================================
# Applying Verified Repairs
# =========================================================


def apply_verified_repair(
    *,
    target_file: str,
    original_code: str,
    repaired_code: str,
) -> None:
    """Apply the exact candidate code that passed sandbox verification."""
    patch = generate_patch(
        original_code=original_code,
        repaired_code=repaired_code,
        filename=os.path.basename(target_file),
    )

    info("\n--- VERIFIED PATCH ---")
    if patch.strip():
        print(patch)
    else:
        print("(The verified candidate is textually identical to the original source.)")
    info("----------------------\n")

    with open(target_file, "w", encoding="utf-8") as file_handle:
        file_handle.write(repaired_code)


# =========================================================
# Main Execution
# =========================================================


def main() -> None:
    """Execute one CLEAR autonomous repair task."""
    parser = argparse.ArgumentParser(
        prog="CLEAR Single Execution Orchestrator",
        description=(
            "Run one sandbox-verified autonomous "
            "Python repair task."
        ),
    )

    parser.add_argument(
        "--code",
        required=True,
        help="Path to the broken target.py",
    )
    parser.add_argument(
        "--test",
        required=True,
        help="Path to the test_target.py oracle",
    )
    parser.add_argument(
        "--recursion-limit",
        type=int,
        default=DEFAULT_RECURSION_LIMIT,
        help=(
            "LangGraph recursion limit. "
            f"Default: {DEFAULT_RECURSION_LIMIT}."
        ),
    )

    arguments = parser.parse_args()

    if arguments.recursion_limit < 3:
        parser.error("--recursion-limit must be at least 3.")

    target_file = os.path.abspath(arguments.code)
    test_file = os.path.abspath(arguments.test)

    benchmark_name = get_benchmark_name(target_file)
    benchmark_directory = os.path.dirname(target_file)

    if benchmark_directory not in sys.path:
        sys.path.insert(0, benchmark_directory)

    info("=" * 60)
    info(f"Initializing CLEAR Hybrid Orchestrator for: {benchmark_name}")
    info("=" * 60 + "\n")

    status = "FAILED"
    failure_reason: str | None = None
    execution_time = 0.0
    iterations = 0
    verified = False

    # =====================================================
    # Load Files
    # =====================================================

    try:
        broken_code = read_text_file(target_file)
        test_suite = read_text_file(test_file)

    except FileNotFoundError as exc:
        failure_reason = f"Missing benchmark file: {exc.filename}"
        failure(f"REPAIR_FAILED | Benchmark={benchmark_name} | Reason={failure_reason}")
        print_result(
            status=status,
            benchmark=benchmark_name,
            reason=failure_reason,
            execution_time=execution_time,
            iterations=iterations,
            verified=verified,
        )
        raise SystemExit(1)

    except (PermissionError, OSError) as exc:
        failure_reason = f"Benchmark file access failure: {exc}"
        failure(f"REPAIR_FAILED | Benchmark={benchmark_name} | Reason={failure_reason}")
        print_result(
            status=status,
            benchmark=benchmark_name,
            reason=failure_reason,
            execution_time=execution_time,
            iterations=iterations,
            verified=verified,
        )
        raise SystemExit(1)

    if not broken_code.strip():
        failure_reason = "Target source file is empty"
        failure(f"REPAIR_FAILED | Benchmark={benchmark_name} | Reason={failure_reason}")
        print_result(
            status=status,
            benchmark=benchmark_name,
            reason=failure_reason,
            execution_time=execution_time,
            iterations=iterations,
            verified=verified,
        )
        raise SystemExit(1)

    if not test_suite.strip():
        failure_reason = "Validation test suite is empty"
        failure(f"REPAIR_FAILED | Benchmark={benchmark_name} | Reason={failure_reason}")
        print_result(
            status=status,
            benchmark=benchmark_name,
            reason=failure_reason,
            execution_time=execution_time,
            iterations=iterations,
            verified=verified,
        )
        raise SystemExit(1)

    # =====================================================
    # Construct Graph State
    # =====================================================

    instruction = build_repair_instruction(
        broken_code=broken_code,
        test_suite=test_suite,
    )

    initial_state: AgentState = {
        "messages": [HumanMessage(content=instruction)],
        "test_suite": test_suite,
        "invalid_responses": 0,
        "terminal_failure": None,
        "last_candidate": None,
        "duplicate_candidates": 0,
    } # type: ignore

    graph_config: RunnableConfig = {
        "recursion_limit": arguments.recursion_limit,
    }

    final_state: AgentState | None = None
    recursion_error = False
    system_exception: Exception | None = None

    print("[WAIT] Agent deployed. Executing repair graph...\n")
    start_time = time.perf_counter()

    # =====================================================
    # Execute Graph
    # =====================================================

    try:
        for event in clear_agent.stream(
            initial_state,
            config=graph_config,
            stream_mode="values",
        ):
            typed_event = cast(
                AgentState,
                event,
            )

            final_state = typed_event

            last_message = typed_event[
                "messages"
            ][-1]

            display_stream_message(
                last_message
            )

    except GraphRecursionError:
        recursion_error = True
        warning("Graph recursion limit reached. The repair budget was exhausted.")

    except KeyboardInterrupt:
        warning("Repair execution interrupted by the user.")
        system_exception = KeyboardInterrupt() # type: ignore

    except Exception as exc:
        system_exception = exc
        warning(f"Graph execution collapsed: {type(exc).__name__}: {exc}")

    execution_time = time.perf_counter() - start_time

    print(f"\nTime to Resolution: {execution_time:.2f}s")
    print("=" * 60 + "\n")

    # =====================================================
    # Inspect Graph Output
    # =====================================================

    messages: Sequence[BaseMessage] = []

    if final_state is not None:
        messages = final_state["messages"]
        iterations = count_repair_attempts(messages)

    repaired_code, successful_payload = find_successful_repair(messages)

    # =====================================================
    # Successful Repair
    # =====================================================

    if repaired_code is not None:
        verified = True

        try:
            apply_verified_repair(
                target_file=target_file,
                original_code=broken_code,
                repaired_code=repaired_code,
            )

        except OSError as exc:
            failure_reason = f"Verified repair could not be applied: {exc}"
            failure(f"REPAIR_FAILED | Benchmark={benchmark_name} | Reason={failure_reason}")

        else:
            status = "SUCCESS"
            failure_reason = None

            success(f"REPAIR_SUCCESS | Benchmark={benchmark_name} | Iterations={iterations}")
            success(f"Successfully applied verified repair to {target_file}")

            if successful_payload:
                sandbox_output = str(successful_payload.get("output", "")).strip()
                if sandbox_output:
                    info(f"Sandbox verification output: {sandbox_output}")

    # =====================================================
    # Failed Repair
    # =====================================================

    else:
        latest_failure = find_latest_tool_failure(messages)

        protocol_failure: str | None = None
        if final_state is not None:
            protocol_failure = final_state.get("terminal_failure")

        if protocol_failure:
            failure_reason = protocol_failure

        elif recursion_error:
            failure_reason = (
                "Repair budget exhausted "
                "(Graph recursion limit)"
            )

        elif isinstance(
            system_exception,
            KeyboardInterrupt,
        ):
            failure_reason = "Repair interrupted by user"

        elif system_exception is not None:
            failure_reason = (
                "System crash: "
                f"{type(system_exception).__name__}: "
                f"{system_exception}"
            )

        elif iterations == 0:
            failure_reason = (
                "No valid repair attempt generated"
            )

        else:
            failure_reason = classify_tool_failure(
                latest_failure
            )

        failure(
            f"REPAIR_FAILED | Benchmark={benchmark_name} | "
            f"Reason={failure_reason} | Iterations={iterations}"
        )

        if latest_failure:
            latest_message = str(latest_failure.get("message", "")).strip()
            latest_error = str(latest_failure.get("error", "")).strip()
            latest_output = str(latest_failure.get("output", "")).strip()

            if latest_message:
                print(f"\nLatest sandbox message:\n{latest_message}")

            if latest_error:
                print(f"\nLatest sandbox error:\n{latest_error}")

            if latest_output:
                print(f"\nLatest sandbox output:\n{latest_output}")

    # =====================================================
    # Emit Structured Result
    # =====================================================

    print_result(
        status=status,
        benchmark=benchmark_name,
        reason=failure_reason,
        execution_time=execution_time,
        iterations=iterations,
        verified=verified,
    )

    if status != "SUCCESS":
        raise SystemExit(1)


# =========================================================
# Program Entry Point
# =========================================================


if __name__ == "__main__":
    main()
