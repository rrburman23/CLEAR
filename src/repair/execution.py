"""Execution of one autonomous CLEAR software-repair task."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any, Sequence, cast

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.errors import GraphRecursionError

from src.agent.logic import clear_agent
from src.agent.state import AgentState
from src.repair.paths import get_benchmark_name
from src.repair.presentation import (
    apply_verified_repair,
    display_stream_message,
)
from src.repair.protocol import (
    classify_tool_failure,
    count_repair_attempts,
    emit_clear_result,
    find_latest_tool_failure,
    find_successful_repair,
)
from src.reporting.artifacts import save_standalone_artifacts
from src.utils.config import MODEL_NAME
from src.utils.terminal import failure, info, success, warning


def _read_required_file(path: Path, label: str) -> str:
    """Read and validate one required UTF-8 input file."""

    content = path.read_text(encoding="utf-8")

    if not content.strip():
        raise ValueError(f"{label} is empty")

    return content


def _emit_input_failure(
    *,
    benchmark_name: str,
    reason: str,
) -> int:
    """Emit a consistent failure result before graph execution begins."""

    failure(
        f"REPAIR_FAILED | Benchmark={benchmark_name} | Reason={reason}"
    )
    emit_clear_result(
        status="FAILED",
        benchmark=benchmark_name,
        reason=reason,
        execution_time=0.0,
        iterations=0,
        verified=False,
    )
    return 1


def _build_initial_state(
    *,
    broken_code: str,
    test_suite: str,
) -> AgentState:
    return {
        "messages": [HumanMessage(content="Begin the autonomous repair task.")],
        "original_code": broken_code,
        "test_suite": test_suite,
        "latest_candidate": None,
        "latest_feedback": None,
        "invalid_responses": 0,
        "terminal_failure": None,
        "last_candidate_hash": None,
        "repeated_candidate_count": 0,
        "candidate_hashes": [],
        "verified": None,
        "failure_reason": None,
    }


def _failure_reason(
    *,
    final_state: AgentState | None,
    latest_failure: dict[str, Any] | None,
    recursion_error: bool,
    system_exception: BaseException | None,
    iterations: int,
) -> str:
    protocol_failure = (
        final_state.get("terminal_failure")
        if final_state is not None
        else None
    )

    if protocol_failure:
        return protocol_failure

    if recursion_error:
        return "Repair budget exhausted (Graph recursion limit)"

    if isinstance(system_exception, KeyboardInterrupt):
        return "Repair interrupted by user"

    if system_exception is not None:
        return (
            "System crash: "
            f"{type(system_exception).__name__}: {system_exception}"
        )

    if iterations == 0:
        return "No valid repair attempt generated"

    return classify_tool_failure(latest_failure)


def _print_latest_failure(payload: dict[str, Any] | None) -> None:
    if not payload:
        return

    fields = (
        ("Latest sandbox message", payload.get("message", "")),
        ("Latest sandbox error", payload.get("error", "")),
        ("Latest sandbox output", payload.get("output", "")),
    )

    for heading, value in fields:
        text = str(value).strip()
        if text:
            print(f"\n{heading}:\n{text}")


def run_repair(
    args: argparse.Namespace,
    standalone_run_directory: Path | None,
) -> int:
    """Execute one autonomous repair and return its process exit code."""

    if args.recursion_limit < 3:
        raise ValueError("recursion_limit must be at least 3")

    target_file = Path(args.code).resolve()
    test_file = Path(args.test).resolve()
    benchmark_name = get_benchmark_name(target_file)

    benchmark_directory = str(target_file.parent)
    if benchmark_directory not in sys.path:
        sys.path.insert(0, benchmark_directory)

    info("=" * 60)
    info(f"Initializing CLEAR Hybrid Orchestrator for: {benchmark_name}")
    info("=" * 60 + "\n")

    try:
        broken_code = _read_required_file(target_file, "Target source file")
        test_suite = _read_required_file(test_file, "Validation test suite")
    except FileNotFoundError as exc:
        return _emit_input_failure(
            benchmark_name=benchmark_name,
            reason=f"Missing benchmark file: {exc.filename}",
        )
    except ValueError as exc:
        return _emit_input_failure(
            benchmark_name=benchmark_name,
            reason=str(exc),
        )
    except (PermissionError, OSError) as exc:
        return _emit_input_failure(
            benchmark_name=benchmark_name,
            reason=f"Benchmark file access failure: {exc}",
        )

    initial_state = _build_initial_state(
        broken_code=broken_code,
        test_suite=test_suite,
    )
    graph_config: RunnableConfig = {
        "recursion_limit": args.recursion_limit,
    }

    final_state: AgentState | None = None
    recursion_error = False
    system_exception: BaseException | None = None

    print("[WAIT] Agent deployed. Executing repair graph...\n")
    start_time = time.perf_counter()

    try:
        for event in clear_agent.stream(
            initial_state,
            config=graph_config,
            stream_mode="values",
        ):
            final_state = cast(AgentState, event)
            display_stream_message(final_state["messages"][-1])
    except GraphRecursionError:
        recursion_error = True
        warning("Graph recursion limit reached. The repair budget was exhausted.")
    except KeyboardInterrupt:
        system_exception = KeyboardInterrupt()
        warning("Repair execution interrupted by the user.")
    except Exception as exc:
        system_exception = exc
        warning(f"Graph execution collapsed: {type(exc).__name__}: {exc}")

    execution_time = time.perf_counter() - start_time

    print(f"\nTime to Resolution: {execution_time:.2f}s")
    print("=" * 60 + "\n")

    messages: Sequence[BaseMessage] = []
    if final_state is not None:
        messages = final_state["messages"]

    iterations = count_repair_attempts(messages)
    repaired_code, successful_payload = find_successful_repair(messages)

    status = "FAILED"
    verified = False
    failure_reason: str | None = None
    repair_patch: str | None = None

    if repaired_code is not None:
        try:
            repair_patch = apply_verified_repair(
                target_file=str(target_file),
                original_code=broken_code,
                repaired_code=repaired_code,
            )
        except OSError as exc:
            failure_reason = f"Verified repair could not be applied: {exc}"
            failure(
                f"REPAIR_FAILED | Benchmark={benchmark_name} | "
                f"Reason={failure_reason}"
            )
        else:
            status = "SUCCESS"
            verified = True

            success(
                f"REPAIR_SUCCESS | Benchmark={benchmark_name} | "
                f"Iterations={iterations}"
            )
            success(f"Successfully applied verified repair to {target_file}")

            if successful_payload:
                sandbox_output = str(
                    successful_payload.get("output", "")
                ).strip()
                if sandbox_output:
                    info(f"Sandbox verification output: {sandbox_output}")
    else:
        latest_failure = find_latest_tool_failure(messages)
        failure_reason = _failure_reason(
            final_state=final_state,
            latest_failure=latest_failure,
            recursion_error=recursion_error,
            system_exception=system_exception,
            iterations=iterations,
        )

        failure(
            f"REPAIR_FAILED | Benchmark={benchmark_name} | "
            f"Reason={failure_reason} | Iterations={iterations}"
        )
        _print_latest_failure(latest_failure)

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

    emit_clear_result(
        status=status,
        benchmark=benchmark_name,
        reason=failure_reason,
        execution_time=execution_time,
        iterations=iterations,
        verified=verified,
    )

    return 0 if verified else 1
