"""CLI entry point for one autonomous CLEAR repair task."""

from __future__ import annotations

import os
from contextlib import nullcontext
from pathlib import Path
from typing import ContextManager

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
from src.utils.terminal import info, warning


def _benchmark_mode_enabled() -> bool:
    return os.getenv("CLEAR_BENCHMARK_MODE", "false").strip().lower() == "true"


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

    save_run_ignored = args.save_run and benchmark_mode

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

        exit_code = run_repair(
            args=args,
            standalone_run_directory=standalone_run_directory,
        )

        if standalone_run_directory is not None:
            info(f"Standalone artefacts saved to: {standalone_run_directory}")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
