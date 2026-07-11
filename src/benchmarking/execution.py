"""Isolated execution of individual CLEAR benchmark cases."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from src.benchmarking.failures import (
    count_repair_attempts,
    derive_failure_reason,
    extract_clear_result,
    normalise_timeout_output,
)
from src.benchmarking.models import BenchmarkResult, BenchmarkTask


def _coerce_int(value: Any, default: int = 0) -> int:
    """Convert an arbitrary telemetry value to ``int`` safely."""

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_float(value: Any, default: float) -> float:
    """Convert an arbitrary telemetry value to ``float`` safely."""

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _build_environment(model: str, project_root: str) -> dict[str, str]:
    """Build the child-process environment for one model execution."""

    environment = os.environ.copy()
    environment["CLEAR_MODEL"] = model

    existing_pythonpath = environment.get("PYTHONPATH", "")

    environment["PYTHONPATH"] = (
        project_root
        if not existing_pythonpath
        else project_root + os.pathsep + existing_pythonpath
    )

    return environment


def _restore_target(target_file: Path, original_code: str) -> None:
    """Restore the exact source captured before benchmark execution."""

    target_file.write_text(original_code, encoding="utf-8")


def execute_benchmark(
    *,
    model: str,
    task: BenchmarkTask,
    project_root: str,
    timeout_seconds: float,
    max_iterations: int,
) -> BenchmarkResult:
    """Execute one model against one benchmark in a child process.

    The function always restores the original faulty ``target.py`` in a
    ``finally`` block.  This guarantees that every model receives identical
    seeded source code even when the child process fails or times out.
    """

    target_path = Path(task.target_file)
    original_code = target_path.read_text(encoding="utf-8")

    command = [
        sys.executable,
        "-m",
        "src.main",
        "--code",
        task.target_file,
        "--test",
        task.test_file,
    ]

    process_returncode: int | None = None
    stdout = ""
    stderr = ""
    clear_result: dict[str, Any] | None = None
    timed_out = False

    wall_start = time.perf_counter()

    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=_build_environment(model, project_root),
            cwd=task.root,
            timeout=timeout_seconds,
            check=False,
        )

        process_returncode = process.returncode
        stdout = process.stdout or ""
        stderr = process.stderr or ""
        clear_result = extract_clear_result(stdout)

    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = normalise_timeout_output(exc.stdout)
        stderr = normalise_timeout_output(exc.stderr)

        logging.error(
            "%s timed out after %.2f seconds.",
            task.benchmark_id,
            timeout_seconds,
        )

    except Exception as exc:
        stderr = f"{type(exc).__name__}: {exc}"

        logging.exception(
            "Unexpected execution error for %s.",
            task.benchmark_id,
        )

    finally:
        try:
            _restore_target(target_path, original_code)
        except OSError as restore_error:
            logging.critical(
                "Unable to restore benchmark source %s: %s",
                target_path,
                restore_error,
            )

    wall_time = time.perf_counter() - wall_start

    fallback_iterations = count_repair_attempts(stdout)

    if clear_result:
        iterations = _coerce_int(
            clear_result.get("iterations"),
            fallback_iterations,
        )
        ttr = _coerce_float(clear_result.get("time"), wall_time)
        status = str(clear_result.get("status", "")).upper()
        verified = clear_result.get("verified") is True

        passed = bool(
            status == "SUCCESS"
            and verified
            and 0 < iterations <= max_iterations
        )
    else:
        iterations = fallback_iterations
        ttr = wall_time
        verified = False
        passed = False

    failure_reason = None

    if not passed:
        failure_reason = derive_failure_reason(
            clear_result=clear_result,
            process_returncode=process_returncode,
            stdout=stdout,
            stderr=stderr,
            timed_out=timed_out,
            iterations=iterations,
            max_iterations=max_iterations,
        )

        logging.warning(
            (
                "Repair failed | Model=%s | Difficulty=%s | Tier=%s | "
                "Category=%s | Benchmark=%s | Reason=%s | Iterations=%d | "
                "TTR=%.3fs | WallTime=%.3fs | ReturnCode=%s"
            ),
            model,
            task.difficulty.name,
            task.difficulty.code,
            task.category,
            task.benchmark,
            failure_reason,
            iterations,
            ttr,
            wall_time,
            process_returncode,
        )

        if stdout.strip():
            logging.warning(
                "Child stdout for %s:\n%s",
                task.benchmark_id,
                stdout,
            )

        if stderr.strip():
            logging.warning(
                "Child stderr for %s:\n%s",
                task.benchmark_id,
                stderr,
            )

    return BenchmarkResult(
        model=model,
        difficulty=task.difficulty.name,
        difficulty_tier=task.difficulty.tier,
        difficulty_code=task.difficulty.code,
        difficulty_label=task.difficulty.label,
        difficulty_definition=task.difficulty.definition,
        category=task.category,
        benchmark=task.benchmark,
        benchmark_id=task.benchmark_id,
        passed=passed,
        verified=verified,
        ttr=ttr,
        wall_time=wall_time,
        iterations=iterations,
        failure_reason=failure_reason,
        return_code=process_returncode,
        timed_out=timed_out,
    )
