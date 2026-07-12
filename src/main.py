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

from contextlib import nullcontext
from pathlib import Path
from typing import Any, ContextManager, Sequence, cast

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    ToolMessage,
)
from langchain_core.runnables import RunnableConfig
from langgraph.errors import GraphRecursionError

from src.reporting.artifacts import (
    create_standalone_run_directory,
    mirror_console_output,
    save_standalone_artifacts,
)
from src.utils.config import MODEL_NAME
from src.agent.candidate import hash_candidate
from src.agent.logic import clear_agent
from src.agent.state import AgentState
from src.utils.diff import generate_patch
from src.utils.terminal import failure, info, success, warning


# =========================================================
# Configuration
# =========================================================

DEFAULT_RECURSION_LIMIT = 31
MESSAGE_PREVIEW_LIMIT = 150

DIFFICULTY_DIRECTORIES = {
    "single_fault",
    "compound_same_category",
    "compound_cross_category",
}


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
# Command-Line Interface
# =========================================================


def create_parser() -> argparse.ArgumentParser:
    """
    Create the command-line parser for one CLEAR repair execution.

    Argument definition is kept separate from repair execution so that:

    - main() handles command-line input;
    - run_repair() handles the repair process;
    - tests can construct an argparse.Namespace directly when needed.
    """

    parser = argparse.ArgumentParser(
        prog="python -m src.main",
        description=(
            "Run one autonomous CLEAR software-repair task against a "
            "target Python file and its verification suite."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:

  Run one repair:
      python -m src.main --code path/to/target.py --test path/to/test_target.py

  Save standalone repair artefacts:
      python -m src.main --code path/to/target.py --test path/to/test_target.py --save-run

  Use a custom standalone output directory:
      python -m src.main --code path/to/target.py --test path/to/test_target.py --save-run --log-dir tests/manual_runs
""",
    )

    parser.add_argument(
        "--code",
        required=True,
        metavar="PATH",
        help="Path to the intentionally faulty target.py file.",
    )

    parser.add_argument(
        "--test",
        required=True,
        metavar="PATH",
        help="Path to the pytest verification suite.",
    )

    parser.add_argument(
        "--recursion-limit",
        type=int,
        default=DEFAULT_RECURSION_LIMIT,
        metavar="N",
        help=(
            f"Maximum LangGraph recursion steps. Default: {DEFAULT_RECURSION_LIMIT}."
        ),
    )

    parser.add_argument(
        "--save-run",
        action="store_true",
        help=(
            "Save standalone execution artefacts including the original "
            "source, test suite, repaired source, unified diff, result JSON, "
            "and execution log."
        ),
    )

    parser.add_argument(
        "--log-dir",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "Base directory for standalone repair artefacts. "
            "Default: tests/logs/single_runs."
        ),
    )

    return parser

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
    Build a benchmark identifier from legacy or tiered benchmark paths.

    Tiered:
        tests/benchmarks/single_fault/concurrency/thread_lock/target.py
        -> single_fault:concurrency:thread_lock

    Legacy:
        tests/benchmarks/logic/factorial/target.py
        -> logic:factorial
    """

    parts = Path(path).resolve().parts

    try:
        benchmark_index = parts.index("benchmarks")
    except ValueError:
        return "unknown"

    relative_parts = parts[benchmark_index + 1 : -1]

    if len(relative_parts) >= 3 and relative_parts[0] in DIFFICULTY_DIRECTORIES:
        difficulty = relative_parts[0]
        category = relative_parts[1]
        benchmark = relative_parts[2]

        return f"{difficulty}:{category}:{benchmark}"

    if len(relative_parts) >= 2:
        category = relative_parts[0]
        benchmark = relative_parts[1]

        return f"{category}:{benchmark}"

    return "unknown"


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

    if any(marker in combined_feedback for marker in ("docker", "container", "daemon")):
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
            tool_name = tool_call.get("name", "unknown")
            tool_arguments = tool_call.get("args", {})

            print(f"   Tool Requested: {tool_name}")

            if not isinstance(tool_arguments, dict):
                continue

            candidate_code = tool_arguments.get("code")

            if isinstance(candidate_code, str) and candidate_code.strip():
                candidate_hash = hash_candidate(candidate_code)

                print(
                    f"   Candidate: {candidate_hash} ({len(candidate_code)} characters)"
                )

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
) -> str:
    """Apply verified code and return its unified diff."""

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

    with open(
        target_file,
        "w",
        encoding="utf-8",
    ) as file_handle:
        file_handle.write(repaired_code)

    return patch


# =========================================================
# Repair Execution
# =========================================================


def run_repair(
    args: argparse.Namespace,
    standalone_run_directory: Path | None,
) -> int:
    """
    Execute one autonomous repair task.

    Args:
        args:
            Parsed command-line arguments.

        standalone_run_directory:
            Optional output directory for a manually requested standalone
            execution. This remains None when src.main is launched by the
            benchmark runner.

    Returns:
        Zero when a verified repair is successfully applied.
        One when the repair fails or cannot be applied.
    """
    
    if args.recursion_limit < 3:
        raise ValueError("recursion_limit must be at least 3")
    
    target_file = os.path.abspath(
        args.code
    )

    test_file = os.path.abspath(
        args.test
    )

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
    repaired_code: str | None = None
    repair_patch: str | None = None

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
        "last_candidate_hash": None,
        "repeated_candidate_count": 0,
    }

    graph_config: RunnableConfig = {
        "recursion_limit": args.recursion_limit,
    }

    final_state: AgentState | None = None
    recursion_error = False
    system_exception: BaseException | None = None

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

            last_message = typed_event["messages"][-1]

            display_stream_message(last_message)

    except GraphRecursionError:
        recursion_error = True
        warning("Graph recursion limit reached. The repair budget was exhausted.")

    except KeyboardInterrupt:
        warning("Repair execution interrupted by the user.")
        system_exception = KeyboardInterrupt()

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
        try:
            repair_patch = apply_verified_repair(
                target_file=target_file,
                original_code=broken_code,
                repaired_code=repaired_code,
            )

        except OSError as exc:
            verified = False
            status = "FAILED"
            failure_reason = (
                f"Verified repair could not be applied: {exc}"
            )

            failure(
                f"REPAIR_FAILED | Benchmark={benchmark_name} | "
                f"Reason={failure_reason}"
            )

        else:
            verified = True
            status = "SUCCESS"
            failure_reason = None

            success(
                f"REPAIR_SUCCESS | Benchmark={benchmark_name} | "
                f"Iterations={iterations}"
            )

            success(
                f"Successfully applied verified repair to {target_file}"
            )

            if successful_payload:
                sandbox_output = str(
                    successful_payload.get(
                        "output",
                        "",
                    )
                ).strip()

                if sandbox_output:
                    info(
                        f"Sandbox verification output: "
                        f"{sandbox_output}"
                    )

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
            failure_reason = "Repair budget exhausted (Graph recursion limit)"

        elif isinstance(
            system_exception,
            KeyboardInterrupt,
        ):
            failure_reason = "Repair interrupted by user"

        elif system_exception is not None:
            failure_reason = (
                f"System crash: {type(system_exception).__name__}: {system_exception}"
            )

        elif iterations == 0:
            failure_reason = "No valid repair attempt generated"

        else:
            failure_reason = classify_tool_failure(latest_failure)

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
    result_payload = {
        "status": status,
        "benchmark": benchmark_name,
        "model": MODEL_NAME,
        "reason": failure_reason,
        "time": execution_time,
        "iterations": iterations,
        "verified": verified,
    }

    if standalone_run_directory is not None:
        save_standalone_artifacts(
            run_directory=standalone_run_directory,
            original_code=broken_code,
            test_suite=test_suite,
            repaired_code=repaired_code,
            patch=repair_patch,
            result=result_payload,
        )

    print_result(
        status=status,
        benchmark=benchmark_name,
        reason=failure_reason,
        execution_time=execution_time,
        iterations=iterations,
        verified=verified,
    )

    return 0 if verified else 1


# =========================================================
# Main Entry Point
# =========================================================


def main() -> int:
    """
    Parse command-line arguments and optionally enable standalone logging.
    """

    parser = create_parser()
    args = parser.parse_args()

    if args.recursion_limit < 3:
        parser.error("--recursion-limit must be at least 3.")

    benchmark_name = get_benchmark_name(args.code)

    benchmark_mode = (
        os.getenv(
            "CLEAR_BENCHMARK_MODE",
            "false",
        ).lower()
        == "true"
    )

    standalone_run_directory: Path | None = None

    if args.save_run and not benchmark_mode:
        standalone_run_directory = create_standalone_run_directory(
            model=MODEL_NAME,
            benchmark=benchmark_name,
            base_directory=args.log_dir,
        )

    elif args.save_run and benchmark_mode:
        warning(
            "--save-run was ignored because src.main is running "
            "under the benchmark runner."
        )

    output_context: ContextManager[None]

    if standalone_run_directory is not None:
        output_context = mirror_console_output(
            standalone_run_directory / "execution.log"
        )
    else:
        output_context = nullcontext()

    with output_context:
        exit_code = run_repair(
            args=args,
            standalone_run_directory=standalone_run_directory,
        )

        if standalone_run_directory is not None:
            info(f"Standalone artefacts saved to: {standalone_run_directory}")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())