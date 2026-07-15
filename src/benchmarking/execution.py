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
from src.benchmarking.validation import (
    BenchmarkInfrastructureError,
    verify_test_collection,
    verify_fault_is_observable,
)

from src.utils.diff import generate_patch


# =========================================================
# Telemetry Conversion
# =========================================================


def _coerce_int(
    value: Any,
    default: int = 0,
) -> int:
    """Convert an arbitrary telemetry value to an integer safely."""

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_float(
    value: Any,
    default: float,
) -> float:
    """Convert an arbitrary telemetry value to a float safely."""

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# =========================================================
# Child-Process Environment
# =========================================================


def _build_environment(
    model: str,
    project_root: str,
) -> dict[str, str]:
    """
    Build the environment for one src.main child process.

    CLEAR_BENCHMARK_MODE prevents src.main from creating a separate
    standalone logging directory for every model-benchmark pair.
    """

    custom_environment = os.environ.copy()

    custom_environment["CLEAR_MODEL"] = model
    custom_environment["CLEAR_BENCHMARK_MODE"] = "true"

    existing_pythonpath = custom_environment.get(
        "PYTHONPATH",
        "",
    )

    if existing_pythonpath:
        custom_environment["PYTHONPATH"] = (
            project_root + os.pathsep + existing_pythonpath
        )
    else:
        custom_environment["PYTHONPATH"] = project_root

    return custom_environment


# =========================================================
# Benchmark Source Restoration
# =========================================================


def _restore_target(
    target_path: Path,
    original_code: str,
) -> None:
    """Restore the exact faulty source captured before execution."""

    target_path.write_text(
        original_code,
        encoding="utf-8",
    )


# =========================================================
# Verified Repair Capture
# =========================================================


def _capture_verified_repair(
    *,
    target_path: Path,
    original_code: str,
    benchmark_id: str,
) -> tuple[str | None, str | None]:
    """
    Capture repaired source and its unified diff before target restoration.

    Returns:
        A tuple containing:

        - repaired source code;
        - unified diff patch.

    The patch is None when the verified candidate is textually identical
    to the original source.
    """

    try:
        repaired_code = target_path.read_text(encoding="utf-8")

    except OSError as exc:
        logging.error(
            "Verified repair artefact could not be read for %s: %s",
            benchmark_id,
            exc,
        )

        return None, None

    repair_patch: str | None = None

    if repaired_code != original_code:
        repair_patch = generate_patch(
            original_code=original_code,
            repaired_code=repaired_code,
            filename=target_path.name,
        )

    return repaired_code, repair_patch


# =========================================================
# Individual Benchmark Execution
# =========================================================


def execute_benchmark(
    *,
    model: str,
    task: BenchmarkTask,
    project_root: str,
    timeout_seconds: float,
    max_iterations: int,
) -> BenchmarkResult:
    """
    Execute one model against one benchmark in a child process.

    The original faulty target is always restored in a finally block. This
    guarantees that every model receives the same seeded source program.

    A verified repair is captured before restoration so the reporting layer
    can export the repaired source and unified diff.
    """
    target_path = Path(task.target_file)
    test_path = Path(task.test_file)
    benchmark_id = task.benchmark_id

    # Validate the human-authored pytest oracle before launching Ollama.
    # A broken or empty test suite is an experiment infrastructure problem,
    # not evidence that the evaluated model failed to repair the program.
    try:
        collected_tests = verify_test_collection(test_path)
        verify_fault_is_observable(
            target_file=Path(task.target_file),
            test_file=Path(task.test_file),
        )

    except BenchmarkInfrastructureError as exc:
        raise BenchmarkInfrastructureError(
            f"{benchmark_id}: {exc}"
        ) from exc

    logging.info(
        (
            "Benchmark collection verified | Benchmark=%s | "
            "TestFile=%s | CollectedTests=%d"
        ),
        benchmark_id,
        test_path,
        collected_tests,
    )

    original_code = target_path.read_text(encoding="utf-8")

    command = [
        sys.executable,
        "-m",
        "src.main",
        "--code",
        str(target_path),
        "--test",
        str(test_path),
]

    process_returncode: int | None = None

    stdout = ""
    stderr = ""

    clear_result: dict[str, Any] | None = None
    timed_out = False

    repaired_code: str | None = None
    repair_patch: str | None = None

    wall_start = time.perf_counter()

    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=_build_environment(
                model,
                project_root,
            ),
            cwd=task.root,
            timeout=timeout_seconds,
            check=False,
        )

        process_returncode = process.returncode
        stdout = process.stdout or ""
        stderr = process.stderr or ""

        clear_result = extract_clear_result(stdout)

        if clear_result is not None:
            child_status = str(
                clear_result.get(
                    "status",
                    "",
                )
            ).upper()

            if child_status == "INFRASTRUCTURE_ERROR":
                infrastructure_reason = str(
                    clear_result.get("reason")
                    or clear_result.get("message")
                    or (
                        "The benchmark child process reported an "
                        "infrastructure error."
                    )
                )

                raise BenchmarkInfrastructureError(
                    f"{benchmark_id}: {infrastructure_reason}"
                )

        provisional_success = bool(
            clear_result
            and str(
                clear_result.get(
                    "status",
                    "",
                )
            ).upper()
            == "SUCCESS"
            and clear_result.get("verified") is True
        )

        # This must happen before the finally block restores target.py.
        if provisional_success:
            repaired_code, repair_patch = _capture_verified_repair(
                target_path=target_path,
                original_code=original_code,
                benchmark_id=benchmark_id,
            )

    except subprocess.TimeoutExpired as exc:
        timed_out = True

        stdout = normalise_timeout_output(exc.stdout)
        stderr = normalise_timeout_output(exc.stderr)

        logging.error(
            "%s timed out after %.2f seconds.",
            benchmark_id,
            timeout_seconds,
        )

    except BenchmarkInfrastructureError:
        # Propagate infrastructure errors to the experiment runner.
        # The finally block still restores the benchmark target.
        raise

    except Exception as exc:
        stderr = f"{type(exc).__name__}: {exc}"

        logging.exception(
            "Unexpected execution error for %s.",
            benchmark_id,
        )

    finally:
        try:
            _restore_target(
                target_path,
                original_code,
            )

        except OSError as restore_error:
            logging.critical(
                "Unable to restore benchmark source %s: %s",
                target_path,
                restore_error,
            )

    wall_time = time.perf_counter() - wall_start

    # =====================================================
    # Authoritative Result Interpretation
    # =====================================================

    fallback_iterations = count_repair_attempts(stdout)

    if clear_result:
        iterations = _coerce_int(
            clear_result.get("iterations"),
            fallback_iterations,
        )

        ttr = _coerce_float(
            clear_result.get("time"),
            wall_time,
        )

        status = str(
            clear_result.get(
                "status",
                "",
            )
        ).upper()

        verified = clear_result.get("verified") is True

        passed = bool(
            status == "SUCCESS" and verified and 0 < iterations <= max_iterations
        )

    else:
        iterations = fallback_iterations
        ttr = wall_time
        verified = False
        passed = False

    failure_reason: str | None = None

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
                "Category=%s | Benchmark=%s | Reason=%s | "
                "Iterations=%d | TTR=%.3fs | WallTime=%.3fs | "
                "ReturnCode=%s"
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

        # Do not export apparent repair artefacts for an invalid success.
        repaired_code = None
        repair_patch = None

    # Preserve child output for successful and failed attempts.
    if stdout.strip():
        logging.info(
            "Child stdout for %s:\n%s",
            benchmark_id,
            stdout,
        )

    if stderr.strip():
        logging.warning(
            "Child stderr for %s:\n%s",
            benchmark_id,
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
        benchmark_id=benchmark_id,
        passed=passed,
        verified=verified,
        ttr=ttr,
        wall_time=wall_time,
        iterations=iterations,
        failure_reason=failure_reason,
        return_code=process_returncode,
        timed_out=timed_out,
        _repair_patch=repair_patch,
        _repaired_code=repaired_code,
    )
