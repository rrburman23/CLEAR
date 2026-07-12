"""Experiment orchestration for CLEAR multi-model benchmark evaluation."""

from __future__ import annotations

import logging
import re
import subprocess
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from src.utils.config import EXPERIMENT_TYPE
from src.benchmarking.difficulty import DIFFICULTIES, ordered_difficulties
from src.benchmarking.discovery import discover_benchmarks
from src.benchmarking.execution import execute_benchmark
from src.benchmarking.metrics import (
    build_failure_summary,
    summarise_by_difficulty,
    summarise_by_model,
    summarise_by_model_difficulty,
)
from src.benchmarking.models import (
    BenchmarkResult,
    BenchmarkTask,
    ExperimentSettings,
)
from src.reporting.exporter import export_experiment
from src.utils.terminal import failure, info, success, warning


def make_filename_safe(value: str) -> str:
    """Convert arbitrary text into a Windows-safe filename component."""

    normalised = value.replace(":", "-")
    normalised = re.sub(r"[^A-Za-z0-9._+-]+", "-", normalised)
    return normalised.strip("-")


def create_run_directory(
    *,
    project_root: Path,
    settings: ExperimentSettings,
) -> Path:
    """Create and return the isolated output directory for one experiment."""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_component = "_".join(
        make_filename_safe(model) for model in settings.models
    )

    # Avoid Windows MAX_PATH problems during full multi-model experiments.
    if len(model_component) > 80:
        model_component = f"{len(settings.models)}-models"

    difficulty_component = (
        "+".join(DIFFICULTIES[name].code for name in settings.difficulties)
        if settings.difficulties
        else "all-tiers"
    )
    category_component = (
        "+".join(make_filename_safe(item) for item in settings.categories)
        if settings.categories
        else "all-categories"
    )

    directory_name = (
        f"run_{timestamp}_{model_component}_{difficulty_component}_"
        f"{category_component}_{EXPERIMENT_TYPE}"
    )
    run_directory = project_root / "tests" / "logs" / directory_name
    run_directory.mkdir(parents=True, exist_ok=True)
    return run_directory


def configure_file_logging(run_directory: Path) -> None:
    """Configure file-only logging for the current experiment."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(
                run_directory / "execution.log",
                encoding="utf-8",
            )
        ],
        force=True,
    )


def restore_committed_benchmarks(project_root: Path) -> bool:
    """Restore committed benchmark files after explicit user opt-in."""

    try:
        process = subprocess.run(
            ["git", "restore", "tests/benchmarks"],
            cwd=project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as exc:
        warning(f"Git restoration could not be started: {exc}")
        return False

    if process.returncode != 0:
        diagnostic = process.stderr.strip() or process.stdout.strip()
        warning(f"Git restoration failed: {diagnostic}")
        return False

    success("Benchmarks restored to their committed Git state.")
    return True


def _format_optional(value: Any, format_specification: str) -> str:
    """Format nullable numerical metrics for terminal output."""

    if value is None:
        return "N/A"

    return format(float(value), format_specification)


def display_benchmark_result(result: BenchmarkResult) -> None:
    """Display one coloured benchmark outcome."""

    identifier = f"{result.category}:{result.benchmark}"

    if result.passed:
        success(
            f"{result.difficulty_code:<3} | "
            f"{identifier:<36} | PASSED | "
            f"TTR={result.ttr:7.2f}s | "
            f"Wall={result.wall_time:7.2f}s | "
            f"Iterations={result.iterations}"
        )
        return

    reason = result.failure_reason or "Unknown repair failure"
    failure(
        f"{result.difficulty_code:<3} | "
        f"{identifier:<36} | FAILED | {reason} | "
        f"TTR={result.ttr:7.2f}s | "
        f"Wall={result.wall_time:7.2f}s | "
        f"Iterations={result.iterations}"
    )


def _display_summary_rows(
    title: str,
    rows: list[dict[str, Any]],
    label_builder: Any,
) -> None:
    """Display metric rows using one consistent console format."""

    info(f"\n================ {title} ================")
    info(
        f"{'Model / Group':<48} | {'N':>4} | {'SR':>7} | {'P@1':>7} | "
        f"{'TTR':>9} | {'IE':>7} | {'ARI':>7} | {'FR':>7}"
    )
    info("-" * 118)

    for row in rows:
        label = str(label_builder(row))
        ttr = _format_optional(row.get("mean_ttr_s"), ".2f")
        efficiency = _format_optional(row.get("iteration_efficiency"), ".3f")
        iterations = _format_optional(
            row.get("average_repair_iterations"),
            ".2f",
        )

        line = (
            f"{label:<48} | "
            f"{int(row['attempts']):4d} | "
            f"{float(row['success_rate_pct']):6.1f}% | "
            f"{float(row['pass_at_1_pct']):6.1f}% | "
            f"{ttr:>8} | "
            f"{efficiency:>7} | "
            f"{iterations:>7} | "
            f"{float(row['failure_rate_pct']):6.1f}%"
        )

        success_rate = float(row["success_rate_pct"])

        if success_rate == 100:
            success(line)
        elif success_rate > 0:
            warning(line)
        else:
            failure(line)

    info("=" * 118)


def display_final_reports(results: list[BenchmarkResult]) -> None:
    """Display overall, tiered, and failure summaries."""

    _display_summary_rows(
        "FINAL PERFORMANCE MATRIX",
        summarise_by_model(results),
        lambda row: row["model"],
    )

    _display_summary_rows(
        "AGGREGATE PERFORMANCE BY DIFFICULTY",
        summarise_by_difficulty(results),
        lambda row: f"T{row['difficulty_tier']} {row['difficulty_label']}",
    )

    _display_summary_rows(
        "MODEL PERFORMANCE BY DIFFICULTY",
        summarise_by_model_difficulty(results),
        lambda row: (
            f"{row['model']} / T{row['difficulty_tier']} "
            f"{row['difficulty_label']}"
        ),
    )

    info("\n================ FAILURE ANALYSIS =================")
    failures = build_failure_summary(results)

    if not failures:
        success("No failures recorded.")
    else:
        current_model: str | None = None

        for row in failures:
            model = str(row["model"])

            if model != current_model:
                info(f"\nModel: {model}")
                current_model = model

            count = int(row["count"])
            suffix = "" if count == 1 else "s"
            info(
                f"  - T{row['difficulty_tier']} {row['difficulty_label']} | "
                f"{row['failure_reason']}: {count} occurrence{suffix}"
            )

    info("=" * 53)


def log_breakdown_statistics(results: list[BenchmarkResult]) -> None:
    """Write tier-level aggregate statistics to ``execution.log``."""

    logging.info("================ DIFFICULTY PERFORMANCE ================")

    for row in summarise_by_difficulty(results):
        logging.info(
            (
                "Difficulty=%s | Tier=T%s | Label=%s | Attempts=%d | "
                "Successes=%d | SR=%.2f%% | Pass@1=%.2f%% | "
                "MeanTTR=%s | IE=%s | ARI=%s | FR=%.2f%%"
            ),
            row["difficulty"],
            row["difficulty_tier"],
            row["difficulty_label"],
            row["attempts"],
            row["successes"],
            row["success_rate_pct"],
            row["pass_at_1_pct"],
            (
                f"{row['mean_ttr_s']:.3f}s"
                if row["mean_ttr_s"] is not None
                else "N/A"
            ),
            (
                f"{row['iteration_efficiency']:.3f}"
                if row["iteration_efficiency"] is not None
                else "N/A"
            ),
            (
                f"{row['average_repair_iterations']:.3f}"
                if row["average_repair_iterations"] is not None
                else "N/A"
            ),
            row["failure_rate_pct"],
        )


def _catastrophic_result(
    *,
    model: str,
    task: BenchmarkTask,
    exception: Exception,
) -> BenchmarkResult:
    """Create a valid result record for an unexpected runner exception."""

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
        passed=False,
        verified=False,
        ttr=0.0,
        wall_time=0.0,
        iterations=0,
        failure_reason=(
            f"Benchmark runner crash: {type(exception).__name__}: {exception}"
        ),
        return_code=None,
        timed_out=False,
    )


def _display_experiment_header(
    *,
    settings: ExperimentSettings,
    run_directory: Path,
) -> None:
    """Display and log the immutable experiment configuration."""

    info("=" * 80)
    info("CLEAR MULTI-MODEL BENCHMARK EXPERIMENT")
    info("=" * 80)
    info(f"Experiment type: {EXPERIMENT_TYPE}")
    info(f"Models: {settings.models}")
    info(f"Difficulty levels: {settings.difficulties or 'All'}")
    info(f"Categories: {settings.categories or 'All'}")
    info(f"Maximum repair iterations: {settings.max_iterations}")
    info(f"Per-benchmark timeout: {settings.timeout_seconds:.1f}s")
    info(f"Run directory: {run_directory}")
    info("=" * 80)

    logging.info("Experiment settings: %s", settings.to_dict())


def _display_discovery_summary(tasks: list[BenchmarkTask]) -> None:
    """Display the number of discovered cases in every tier."""

    counts = Counter(task.difficulty.name for task in tasks)
    info(f"Discovered {len(tasks)} benchmark cases.")

    for difficulty in ordered_difficulties():
        count = counts.get(difficulty.name, 0)

        if count:
            info(f"  {difficulty.code} {difficulty.label}: {count}")


def run_experiment(settings: ExperimentSettings) -> Path:
    """Execute the complete sequential benchmark experiment.

    Returns:
        The directory containing the experiment outputs.

    Raises:
        SystemExit: With code 1 when no tasks are discovered, or code 2 when
            catastrophic runner errors occurred.
    """

    project_root = Path(__file__).resolve().parents[2]

    if settings.git_reset_benchmarks:
        restore_committed_benchmarks(project_root)

    run_directory = create_run_directory(
        project_root=project_root,
        settings=settings,
    )
    configure_file_logging(run_directory)
    _display_experiment_header(settings=settings, run_directory=run_directory)

    experiment_start = time.perf_counter()
    logging.info("Experiment started at %s", datetime.now().isoformat())

    tasks = discover_benchmarks(
        project_root / "tests" / "benchmarks",
        selected_categories=settings.categories,
        selected_difficulties=settings.difficulties,
    )

    if not tasks:
        failure("No matching benchmark tasks were discovered.")
        raise SystemExit(1)

    _display_discovery_summary(tasks)

    results: list[BenchmarkResult] = []
    catastrophic_errors = 0

    for model in settings.models:
        info(f"\nEvaluating model: {model}")
        info("=" * 80)
        current_group: tuple[str, str] | None = None

        for task in tasks:
            group = (task.difficulty.name, task.category)

            if group != current_group:
                info(
                    "\n--- "
                    f"{task.difficulty.code} | "
                    f"{task.difficulty.label.upper()} | "
                    f"{task.category.upper()} ---"
                )
                current_group = group

            try:
                result = execute_benchmark(
                    model=model,
                    task=task,
                    project_root=str(project_root),
                    timeout_seconds=settings.timeout_seconds,
                    max_iterations=settings.max_iterations,
                )
            except Exception as exc:
                catastrophic_errors += 1
                logging.exception(
                    "Catastrophic runner error for %s.",
                    task.benchmark_id,
                )
                result = _catastrophic_result(
                    model=model,
                    task=task,
                    exception=exc,
                )

                if settings.stop_on_error:
                    results.append(result)
                    display_benchmark_result(result)
                    export_experiment(results, run_directory, settings)
                    raise

            results.append(result)
            display_benchmark_result(result)

    display_final_reports(results)
    log_breakdown_statistics(results)
    export_experiment(results, run_directory, settings)

    duration = time.perf_counter() - experiment_start
    info("\nBenchmark evaluation completed.")
    info(f"Total experiment duration: {duration:.2f}s")
    info(f"Catastrophic runner errors: {catastrophic_errors}")
    info(f"Outputs saved to: {run_directory}")
    info("=" * 80)

    logging.info("Experiment completed at %s", datetime.now().isoformat())
    logging.info("Total duration: %.3f seconds", duration)

    if catastrophic_errors:
        raise SystemExit(2)

    return run_directory
