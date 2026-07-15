"""CLI entry point for one autonomous CLEAR repair task."""

from __future__ import annotations

import json
import os
import time
from contextlib import nullcontext
from pathlib import Path
from typing import ContextManager

from src.benchmarking.validation import BenchmarkInfrastructureError
from src.repair.cli import create_parser
from src.repair.execution import run_repair
from src.repair.paths import get_benchmark_name
from src.repair.runtime import (
    configure_runtime_logging,
    configure_utf8_output,
)
from src.reporting.artifacts import (
    create_standalone_run_directory,
    mirror_console_output,
)
from src.utils.config import MODEL_NAME
from src.utils.terminal import failure, info, warning


INFRASTRUCTURE_ERROR_EXIT_CODE = 3


def _benchmark_mode_enabled() -> bool:
    """Return whether src.main was launched by the benchmark runner."""

    return (
        os.getenv(
            "CLEAR_BENCHMARK_MODE",
            "false",
        )
        .strip()
        .lower()
        == "true"
    )


def _build_infrastructure_result(
    *,
    benchmark_name: str,
    reason: str,
    elapsed_seconds: float,
) -> dict[str, object]:
    """
    Build the structured child-process result used by the benchmark runner.

    Infrastructure errors are deliberately distinct from ordinary model
    repair failures so that they do not enter SR, FR, Pass@k, TTR, IE or ARI
    calculations.
    """

    return {
        "status": "INFRASTRUCTURE_ERROR",
        "benchmark": benchmark_name,
        "model": MODEL_NAME,
        "reason": reason,
        "time": elapsed_seconds,
        "iterations": 0,
        "verified": False,
    }


def _print_clear_result(
    result: dict[str, object],
) -> None:
    """
    Print one machine-readable CLEAR result envelope.

    src.benchmarking.execution extracts this payload from child-process
    standard output.
    """

    print("\n=== CLEAR_RESULT ===")
    print(
        json.dumps(
            result,
            ensure_ascii=False,
        )
    )
    print("=== END_CLEAR_RESULT ===\n")


def _save_infrastructure_result(
    *,
    run_directory: Path | None,
    result: dict[str, object],
) -> None:
    """Save standalone infrastructure diagnostics when requested."""

    if run_directory is None:
        return

    result_path = run_directory / "result.json"

    result_path.write_text(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def main() -> int:
    """Parse CLI arguments and execute one repair operation."""

    configure_utf8_output()

    parser = create_parser()
    args = parser.parse_args()

    if args.recursion_limit < 3:
        parser.error("--recursion-limit must be at least 3.")

    benchmark_name = get_benchmark_name(args.code)
    benchmark_mode = _benchmark_mode_enabled()

    standalone_run_directory: Path | None = None

    save_run_ignored = bool(args.save_run and benchmark_mode)

    if args.save_run and not benchmark_mode:
        standalone_run_directory = create_standalone_run_directory(
            model=MODEL_NAME,
            benchmark=benchmark_name,
            base_directory=args.log_dir,
        )

    execution_log = (
        standalone_run_directory / "execution.log"
        if standalone_run_directory is not None
        else None
    )

    output_context: ContextManager[None] = (
        mirror_console_output(execution_log)
        if execution_log is not None
        else nullcontext()
    )

    with output_context:
        configure_runtime_logging(
            execution_log=execution_log,
            benchmark_mode=benchmark_mode,
        )

        if save_run_ignored:
            warning(
                "--save-run was ignored because src.main is running "
                "under the benchmark runner."
            )

        operation_start = time.perf_counter()

        try:
            exit_code = run_repair(
                args=args,
                standalone_run_directory=standalone_run_directory,
            )

        except BenchmarkInfrastructureError as exc:
            elapsed_seconds = time.perf_counter() - operation_start

            reason = str(exc)

            infrastructure_result = _build_infrastructure_result(
                benchmark_name=benchmark_name,
                reason=reason,
                elapsed_seconds=elapsed_seconds,
            )

            failure("CLEAR benchmark infrastructure validation failed.")
            failure(f"Benchmark: {benchmark_name}")
            failure(f"Reason: {reason}")

            _print_clear_result(infrastructure_result)

            _save_infrastructure_result(
                run_directory=standalone_run_directory,
                result=infrastructure_result,
            )

            exit_code = INFRASTRUCTURE_ERROR_EXIT_CODE

        if standalone_run_directory is not None:
            info(f"Standalone artefacts saved to: {standalone_run_directory}")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
