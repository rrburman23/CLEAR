"""
CLEAR Multi-Model Benchmark Runner

Executes CLEAR across multiple:

- local language models;
- benchmark difficulty levels;
- fault categories;
- individual benchmark cases.

Expected tiered benchmark structure:

    tests/benchmarks/
    ├── single_fault/
    │   └── logic/
    │       └── factorial/
    │           ├── target.py
    │           └── test_factorial.py
    ├── compound_same_category/
    │   └── logic/
    │       └── multiple_logic_faults/
    │           ├── target.py
    │           └── test_multiple_logic_faults.py
    └── compound_cross_category/
        └── mixed/
            └── logic_and_exception_faults/
                ├── target.py
                └── test_logic_and_exception_faults.py

Legacy structure is also supported:

    tests/benchmarks/logic/factorial/

Legacy benchmarks are automatically classified as Tier 1 single-fault
benchmarks.

For every model-benchmark pair, the runner records:

- model;
- difficulty identifier;
- difficulty tier;
- dissertation difficulty label;
- category;
- benchmark;
- verified repair status;
- time to resolution;
- wall-clock time;
- repair iterations;
- failure reason;
- subprocess return code.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from src.utils.config import AVAILABLE_MODELS
from src.utils.result_export import export_results
from src.utils.terminal import failure, info, success, warning


# =========================================================
# Experiment Configuration
# =========================================================

DIFFICULTY_LEVELS: dict[str, dict[str, Any]] = {
    "single_fault": {
        "tier": 1,
        "code": "T1",
        "label": "Single-Fault Repair",
        "definition": "One intentionally seeded defect",
    },
    "compound_same_category": {
        "tier": 2,
        "code": "T2",
        "label": "Homogeneous Compound-Fault Repair",
        "definition": "Multiple defects from one fault category",
    },
    "compound_cross_category": {
        "tier": 3,
        "code": "T3",
        "label": "Heterogeneous Compound-Fault Repair",
        "definition": "Multiple defects from different categories",
    },
}

AVAILABLE_DIFFICULTIES = list(DIFFICULTY_LEVELS)

AVAILABLE_TYPES = [
    "algorithm",
    "api",
    "concurrency",
    "data_structure",
    "edge_case",
    "exception",
    "logic",
    "mixed",
    "oop",
    "python",
    "security",
    "syntax",
]

DEFAULT_MAX_ITERATIONS = 15
DEFAULT_BENCHMARK_TIMEOUT = 300.0
EXPERIMENT_TYPE = "automated_repair"


# =========================================================
# General Helpers
# =========================================================


def make_filename_safe(value: str) -> str:
    """
    Convert arbitrary text into a filename-safe representation.
    """

    value = value.replace(":", "-")
    value = re.sub(r"[^A-Za-z0-9._+-]+", "-", value)

    return value.strip("-")


def get_difficulty_metadata(
    difficulty: str,
) -> dict[str, Any]:
    """
    Return a copy of the configured difficulty metadata.
    """

    metadata = DIFFICULTY_LEVELS.get(
        difficulty,
        DIFFICULTY_LEVELS["single_fault"],
    )

    return dict(metadata)


# =========================================================
# Logging Configuration
# =========================================================


def setup_logging(
    models: list[str],
    categories: list[str] | None,
    difficulties: list[str] | None,
    experiment_type: str = EXPERIMENT_TYPE,
) -> str:
    """
    Create a dedicated directory for one experiment.

    Example:

        tests/logs/
        └── run_20260711_120000_codegemma-7b_T1+T2_logic_automated_repair/
            ├── execution.log
            ├── dataset.csv
            ├── dataset.json
            ├── summary_by_model.csv
            ├── summary_by_difficulty.csv
            ├── summary_by_model_difficulty.csv
            ├── analysis_report.md
            └── graphs/
    """

    base_log_dir = os.path.abspath("tests/logs")

    os.makedirs(
        base_log_dir,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    model_string = "_".join(make_filename_safe(model) for model in models)

    if len(model_string) > 80:
        model_string = f"{len(models)}-models"

    if difficulties:
        difficulty_string = "+".join(
            DIFFICULTY_LEVELS[difficulty]["code"] for difficulty in difficulties
        )
    else:
        difficulty_string = "all-tiers"

    category_string = (
        "+".join(make_filename_safe(category) for category in categories)
        if categories
        else "all-categories"
    )

    run_folder_name = (
        f"run_{timestamp}_"
        f"{model_string}_"
        f"{difficulty_string}_"
        f"{category_string}_"
        f"{make_filename_safe(experiment_type)}"
    )

    run_dir = os.path.join(
        base_log_dir,
        run_folder_name,
    )

    os.makedirs(
        run_dir,
        exist_ok=True,
    )

    log_file = os.path.join(
        run_dir,
        "execution.log",
    )

    logging.basicConfig(
        level=logging.INFO,
        format=("%(asctime)s - %(levelname)s - %(message)s"),
        handlers=[
            logging.FileHandler(
                log_file,
                encoding="utf-8",
            )
        ],
        force=True,
    )

    return run_dir


# =========================================================
# Command-Line Configuration
# =========================================================


def create_parser() -> argparse.ArgumentParser:
    """
    Construct the benchmark command-line parser.
    """

    available_models_block = "\n".join(f"  - {model}" for model in AVAILABLE_MODELS)

    difficulty_block = "\n".join(
        (f"  - {name}: Tier {metadata['tier']} — {metadata['label']}")
        for name, metadata in DIFFICULTY_LEVELS.items()
    )

    parser = argparse.ArgumentParser(
        prog="CLEAR Benchmark Runner",
        description=(
            "Evaluate local language models on the CLEAR "
            "autonomous program-repair benchmark."
        ),
        formatter_class=(argparse.RawDescriptionHelpFormatter),
        epilog=f"""
Available models:
{available_models_block}

Difficulty levels:
{difficulty_block}

Examples:

  Run every configured model and benchmark:
      python -m run_benchmarks

  Run one model:
      python -m run_benchmarks --models codegemma:7b

  Run only Tier 1:
      python -m run_benchmarks --tiers single_fault

  Run Tier 2 and Tier 3:
      python -m run_benchmarks --tiers compound_same_category compound_cross_category

  Run selected categories:
      python -m run_benchmarks --types logic syntax security

  Combine filters:
      python -m run_benchmarks --models codegemma:7b --tiers single_fault --types logic

  Set a 10-minute timeout:
      python -m run_benchmarks --timeout 600

  Restore committed benchmark files:
      python -m run_benchmarks --git-reset-benchmarks
""",
    )

    parser.add_argument(
        "--models",
        nargs="+",
        choices=AVAILABLE_MODELS,
        metavar="MODEL",
        help=("Models to evaluate. If omitted, all configured models are evaluated."),
    )

    parser.add_argument(
        "--types",
        nargs="+",
        choices=AVAILABLE_TYPES,
        metavar="TYPE",
        help=("Categories to evaluate. If omitted, all categories are evaluated."),
    )

    parser.add_argument(
        "--difficulties",
        "--tiers",
        dest="difficulties",
        nargs="+",
        choices=AVAILABLE_DIFFICULTIES,
        metavar="DIFFICULTY",
        help=("Difficulty levels to evaluate. If omitted, all tiers are evaluated."),
    )

    parser.add_argument(
        "--max-iterations",
        type=int,
        default=DEFAULT_MAX_ITERATIONS,
        metavar="N",
        help=(
            "Maximum accepted repair attempts per benchmark. "
            f"Default: {DEFAULT_MAX_ITERATIONS}."
        ),
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_BENCHMARK_TIMEOUT,
        metavar="SECONDS",
        help=(
            "Maximum wall-clock time allowed for each "
            f"benchmark. Default: {DEFAULT_BENCHMARK_TIMEOUT:.0f}s."
        ),
    )

    parser.add_argument(
        "--git-reset-benchmarks",
        action="store_true",
        help=(
            "Run 'git restore tests/benchmarks' before "
            "evaluation. This discards uncommitted changes "
            "inside that directory."
        ),
    )

    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help=(
            "Stop the complete experiment after a catastrophic benchmark-runner error."
        ),
    )

    return parser


# =========================================================
# Structured Result Parsing
# =========================================================


def extract_clear_result(
    output: str,
) -> dict[str, Any] | None:
    """
    Extract the final machine-readable CLEAR_RESULT block.
    """

    matches = re.findall(
        (
            r"=== CLEAR_RESULT ===\s*"
            r"(.*?)"
            r"\s*=== END_CLEAR_RESULT ==="
        ),
        output,
        re.DOTALL,
    )

    if not matches:
        return None

    for candidate in reversed(matches):
        try:
            result = json.loads(candidate.strip())
        except json.JSONDecodeError:
            continue

        if isinstance(result, dict):
            return result

    return None


def normalise_timeout_output(
    value: str | bytes | None,
) -> str:
    """
    Convert TimeoutExpired output into safe Unicode.
    """

    if value is None:
        return ""

    if isinstance(value, bytes):
        return value.decode(
            "utf-8",
            errors="replace",
        )

    return str(value)


# =========================================================
# Benchmark Discovery
# =========================================================


def infer_benchmark_location(
    benchmark_directory: Path,
    benchmarks_root: Path,
) -> tuple[str, str, str] | None:
    """
    Infer difficulty, category and benchmark from the directory.

    Tiered layout:

        benchmarks/<difficulty>/<category>/<benchmark>/

    Legacy layout:

        benchmarks/<category>/<benchmark>/

    Legacy benchmarks are treated as single_fault.
    """

    relative_path = benchmark_directory.relative_to(benchmarks_root)

    parts = relative_path.parts

    if not parts:
        return None

    if parts[0] in DIFFICULTY_LEVELS:
        if len(parts) < 3:
            return None

        difficulty = parts[0]
        category = parts[1]
        benchmark = parts[-1]

        return (
            difficulty,
            category,
            benchmark,
        )

    if len(parts) < 2:
        return None

    return (
        "single_fault",
        parts[0],
        parts[-1],
    )


def discover_benchmarks(
    benchmarks_dir: str,
    selected_categories: list[str] | None,
    selected_difficulties: list[str] | None,
) -> list[dict[str, Any]]:
    """
    Discover and sort benchmark cases.
    """

    benchmarks_root = Path(benchmarks_dir).resolve()

    tasks: list[dict[str, Any]] = []

    for root, directories, files in os.walk(benchmarks_root):
        del directories

        if "target.py" not in files:
            continue

        root_path = Path(root)

        location = infer_benchmark_location(
            benchmark_directory=root_path,
            benchmarks_root=benchmarks_root,
        )

        if location is None:
            logging.warning(
                "Could not infer benchmark metadata for %s",
                root,
            )
            continue

        difficulty, category_name, benchmark_name = location

        if selected_difficulties and difficulty not in selected_difficulties:
            continue

        if selected_categories and category_name not in selected_categories:
            continue

        target_file = root_path / "target.py"

        candidate_tests = sorted(
            filename
            for filename in files
            if (filename.startswith("test_") and filename.endswith(".py"))
        )

        if not candidate_tests:
            warning(f"No test file found for {target_file}")
            continue

        if len(candidate_tests) > 1:
            logging.warning(
                "Multiple test files found for %s. Using %s.",
                target_file,
                candidate_tests[0],
            )

        test_file = root_path / candidate_tests[0]

        difficulty_metadata = get_difficulty_metadata(difficulty)

        tasks.append(
            {
                "difficulty": difficulty,
                "difficulty_tier": (difficulty_metadata["tier"]),
                "difficulty_code": (difficulty_metadata["code"]),
                "difficulty_label": (difficulty_metadata["label"]),
                "difficulty_definition": (difficulty_metadata["definition"]),
                "category_name": category_name,
                "benchmark_name": benchmark_name,
                "benchmark_id": (f"{difficulty}:{category_name}:{benchmark_name}"),
                "display_id": (f"{category_name}:{benchmark_name}"),
                "root": str(root_path),
                "target_file": str(target_file),
                "test_file": str(test_file),
            }
        )

    tasks.sort(
        key=lambda task: (
            task["difficulty_tier"],
            task["category_name"],
            task["benchmark_name"],
        )
    )

    return tasks


# =========================================================
# Optional Git Restoration
# =========================================================


def restore_committed_benchmarks(
    project_root: str,
) -> bool:
    """
    Restore benchmarks to their committed Git state.
    """

    try:
        process = subprocess.run(
            [
                "git",
                "restore",
                "tests/benchmarks",
            ],
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
        warning(
            "Git restoration failed. "
            f"{process.stderr.strip() or process.stdout.strip()}"
        )
        return False

    success("Benchmarks restored to their committed Git state.")

    return True


# =========================================================
# Failure Classification
# =========================================================


def derive_failure_reason(
    *,
    clear_result: dict[str, Any] | None,
    process_returncode: int | None,
    stdout: str,
    stderr: str,
    timed_out: bool,
    iterations: int,
    max_iterations: int,
) -> str:
    """
    Derive one consistent failure taxonomy label.
    """

    if timed_out:
        return "Agent timeout"

    if clear_result:
        explicit_reason = clear_result.get("reason")

        if isinstance(explicit_reason, str) and explicit_reason.strip():
            return explicit_reason.strip()

        if clear_result.get("verified") is True:
            return "Verified repair could not be applied"

        status = clear_result.get("status")

        if isinstance(status, str) and status.upper() != "SUCCESS":
            return "Repair failed without a detailed reason"

    if iterations > max_iterations:
        return "Repair iteration budget exceeded"

    combined_output = (f"{stdout}\n{stderr}").lower()

    if (
        "no tests ran" in combined_output
        or "collected 0 items" in combined_output
        or "collected zero tests" in combined_output
    ):
        return "Benchmark configuration error (pytest collected zero tests)"

    if (
        "graphrecursionerror" in combined_output
        or "recursion limit" in combined_output
        or "repair budget exhausted" in combined_output
    ):
        return "Repair budget exhausted (Graph recursion limit)"

    if "timeouterror" in combined_output:
        return "Sandbox timeout"

    if "docker" in combined_output and (
        "daemon" in combined_output
        or "container" in combined_output
        or "connection" in combined_output
    ):
        return "Sandbox infrastructure failure"

    if (
        "syntaxerror" in combined_output
        or "indentationerror" in combined_output
        or "taberror" in combined_output
    ):
        return "Malformed candidate code"

    if (
        "assertionerror" in combined_output
        or "sandbox verification failure" in combined_output
        or "tests did not pass" in combined_output
    ):
        return "Sandbox verification failure"

    if process_returncode is not None and process_returncode != 0 and not clear_result:
        return f"No CLEAR_RESULT returned (subprocess exit code {process_returncode})"

    if not clear_result:
        return "No CLEAR_RESULT returned"

    return "Unknown repair failure"


# =========================================================
# Aggregate Storage
# =========================================================


def create_statistics_bucket() -> dict[str, Any]:
    """
    Create an empty metric bucket.
    """

    return {
        "attempts": 0,
        "success": 0,
        "pass_at_1": 0,
        "ttr_sum": 0.0,
        "wall_time_sum": 0.0,
        "ie_sum": 0.0,
        "iterations_sum": 0,
        "errors": 0,
    }


def initialise_model_aggregates(
    models: list[str],
) -> dict[str, dict[str, Any]]:
    """
    Create aggregate storage for every model.
    """

    return {
        model: {
            **create_statistics_bucket(),
            "failure_reasons": {},
            "categories": {},
            "difficulties": {},
            "difficulty_categories": {},
        }
        for model in models
    }


def update_statistics_bucket(
    bucket: dict[str, Any],
    result: dict[str, Any],
) -> None:
    """
    Add one result to a metric bucket.
    """

    bucket["attempts"] += 1

    if result["passed"]:
        iterations = result["iterations"]

        bucket["success"] += 1
        bucket["ttr_sum"] += result["ttr"]
        bucket["wall_time_sum"] += result["wall_time"]
        bucket["iterations_sum"] += iterations

        if iterations == 1:
            bucket["pass_at_1"] += 1

        if iterations > 0:
            bucket["ie_sum"] += 1 / iterations

    else:
        bucket["errors"] += 1


def update_aggregates(
    *,
    aggregates: dict[str, dict[str, Any]],
    result: dict[str, Any],
) -> None:
    """
    Add one result to model, category and difficulty aggregates.
    """

    model = result["model"]
    category = result["category"]
    difficulty = result["difficulty"]

    statistics = aggregates[model]

    update_statistics_bucket(
        statistics,
        result,
    )

    category_statistics = statistics["categories"].setdefault(
        category,
        create_statistics_bucket(),
    )

    update_statistics_bucket(
        category_statistics,
        result,
    )

    difficulty_statistics = statistics["difficulties"].setdefault(
        difficulty,
        create_statistics_bucket(),
    )

    update_statistics_bucket(
        difficulty_statistics,
        result,
    )

    combined_key = f"{difficulty}:{category}"

    combined_statistics = statistics["difficulty_categories"].setdefault(
        combined_key,
        create_statistics_bucket(),
    )

    update_statistics_bucket(
        combined_statistics,
        result,
    )

    if not result["passed"]:
        reason = result["failure_reason"] or "Unknown repair failure"

        failure_reasons = statistics["failure_reasons"]

        failure_reasons[reason] = (
            failure_reasons.get(
                reason,
                0,
            )
            + 1
        )


def calculate_metrics(
    statistics: dict[str, Any],
) -> dict[str, float]:
    """
    Calculate metrics from an aggregate bucket.
    """

    total = statistics["attempts"]
    successful = statistics["success"]

    success_rate = 100 * successful / total if total else 0.0

    failure_rate = 100 * (total - successful) / total if total else 0.0

    pass_at_1 = 100 * statistics["pass_at_1"] / total if total else 0.0

    mean_ttr = statistics["ttr_sum"] / successful if successful else float("nan")

    iteration_efficiency = (
        statistics["ie_sum"] / successful if successful else float("nan")
    )

    average_iterations = (
        statistics["iterations_sum"] / successful if successful else float("nan")
    )

    return {
        "success_rate": success_rate,
        "failure_rate": failure_rate,
        "pass_at_1": pass_at_1,
        "mean_ttr": mean_ttr,
        "iteration_efficiency": (iteration_efficiency),
        "average_iterations": (average_iterations),
    }


# =========================================================
# Individual Benchmark Execution
# =========================================================


def execute_benchmark(
    *,
    model: str,
    task: dict[str, Any],
    project_root: str,
    timeout_seconds: float,
    max_iterations: int,
) -> dict[str, Any]:
    """
    Execute one model against one benchmark.
    """

    benchmark_id = task["benchmark_id"]
    target_file = task["target_file"]
    test_file = task["test_file"]
    root = task["root"]

    with open(
        target_file,
        "r",
        encoding="utf-8",
    ) as file_handle:
        original_code = file_handle.read()

    custom_environment = os.environ.copy()

    custom_environment["CLEAR_MODEL"] = model

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

    command = [
        sys.executable,
        "-m",
        "src.main",
        "--code",
        target_file,
        "--test",
        test_file,
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
            env=custom_environment,
            cwd=root,
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
            benchmark_id,
            timeout_seconds,
        )

    except Exception as exc:
        stderr = f"{type(exc).__name__}: {exc}"

        logging.exception(
            "Unexpected benchmark-runner exception for %s.",
            benchmark_id,
        )

    finally:
        try:
            with open(
                target_file,
                "w",
                encoding="utf-8",
            ) as file_handle:
                file_handle.write(original_code)

        except OSError as restore_error:
            logging.critical(
                "Unable to restore %s: %s",
                target_file,
                restore_error,
            )

    wall_time = time.perf_counter() - wall_start

    if clear_result:
        raw_iterations = clear_result.get(
            "iterations",
            0,
        )

        try:
            iterations = int(raw_iterations)
        except (TypeError, ValueError):
            iterations = 0

        raw_ttr = clear_result.get(
            "time",
            wall_time,
        )

        try:
            ttr = float(raw_ttr)
        except (TypeError, ValueError):
            ttr = wall_time

        result_status = str(
            clear_result.get(
                "status",
                "",
            )
        ).upper()

        repair_success = bool(
            result_status == "SUCCESS"
            and clear_result.get("verified") is True
            and 0 < iterations <= max_iterations
        )

    else:
        iterations = 0
        ttr = wall_time
        repair_success = False

    if repair_success:
        failure_reason = None

    else:
        failure_reason = derive_failure_reason(
            clear_result=clear_result,
            process_returncode=(process_returncode),
            stdout=stdout,
            stderr=stderr,
            timed_out=timed_out,
            iterations=iterations,
            max_iterations=max_iterations,
        )

        logging.warning(
            (
                "Repair failed | "
                "Model=%s | "
                "Difficulty=%s | "
                "Tier=%s | "
                "Category=%s | "
                "Benchmark=%s | "
                "Reason=%s | "
                "Iterations=%d | "
                "TTR=%.3fs | "
                "WallTime=%.3fs | "
                "ReturnCode=%s"
            ),
            model,
            task["difficulty"],
            task["difficulty_code"],
            task["category_name"],
            task["benchmark_name"],
            failure_reason,
            iterations,
            ttr,
            wall_time,
            process_returncode,
        )

        if stdout.strip():
            logging.warning(
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

    return {
        "model": model,
        "difficulty": task["difficulty"],
        "difficulty_tier": (task["difficulty_tier"]),
        "difficulty_code": (task["difficulty_code"]),
        "difficulty_label": (task["difficulty_label"]),
        "difficulty_definition": (task["difficulty_definition"]),
        "category": task["category_name"],
        "benchmark": task["benchmark_name"],
        "benchmark_id": benchmark_id,
        "passed": repair_success,
        "verified": bool(clear_result and clear_result.get("verified") is True),
        "ttr": ttr,
        "wall_time": wall_time,
        "iterations": iterations,
        "failure_reason": failure_reason,
        "return_code": process_returncode,
        "timed_out": timed_out,
    }


# =========================================================
# Terminal Reporting
# =========================================================


def display_benchmark_result(
    result: dict[str, Any],
) -> None:
    """
    Display one benchmark outcome.
    """

    difficulty_code = result["difficulty_code"]

    benchmark_name = f"{result['category']}:{result['benchmark']}"

    if result["passed"]:
        success(
            f"{difficulty_code:<3} | "
            f"{benchmark_name:<36} | "
            f"PASSED | "
            f"TTR={result['ttr']:7.2f}s | "
            f"Wall={result['wall_time']:7.2f}s | "
            f"Iterations={result['iterations']}"
        )

    else:
        failure_reason = result["failure_reason"] or "Unknown repair failure"

        failure(
            f"{difficulty_code:<3} | "
            f"{benchmark_name:<36} | "
            f"FAILED | "
            f"{failure_reason} | "
            f"TTR={result['ttr']:7.2f}s | "
            f"Wall={result['wall_time']:7.2f}s | "
            f"Iterations={result['iterations']}"
        )


def display_metric_line(
    *,
    label: str,
    statistics: dict[str, Any],
) -> None:
    """
    Display one aggregate metric row.
    """

    metrics = calculate_metrics(statistics)

    total = statistics["attempts"]
    successful = statistics["success"]

    if successful:
        ttr_text = f"{metrics['mean_ttr']:7.2f}s"

        ie_text = f"{metrics['iteration_efficiency']:7.3f}"

        ari_text = f"{metrics['average_iterations']:7.2f}"
    else:
        ttr_text = "     N/A"
        ie_text = "    N/A"
        ari_text = "    N/A"

    line = (
        f"{label:<36} | "
        f"{total:4d} | "
        f"{metrics['success_rate']:6.1f}% | "
        f"{metrics['pass_at_1']:6.1f}% | "
        f"{ttr_text} | "
        f"{ie_text} | "
        f"{ari_text} | "
        f"{metrics['failure_rate']:6.1f}%"
    )

    if metrics["success_rate"] == 100:
        success(line)
    elif metrics["success_rate"] > 0:
        warning(line)
    else:
        failure(line)


def display_final_performance_matrix(
    aggregates: dict[str, dict[str, Any]],
) -> None:
    """
    Display overall model performance.
    """

    info("\n================ FINAL PERFORMANCE MATRIX ================")

    info(
        f"{'Model':<36} | "
        f"{'N':>4} | "
        f"{'SR':>7} | "
        f"{'P@1':>7} | "
        f"{'TTR':>9} | "
        f"{'IE':>7} | "
        f"{'ARI':>7} | "
        f"{'FR':>7}"
    )

    info("-" * 106)

    for model, statistics in aggregates.items():
        display_metric_line(
            label=model,
            statistics=statistics,
        )

    info("=" * 106)


def display_difficulty_performance(
    aggregates: dict[str, dict[str, Any]],
) -> None:
    """
    Display model performance separately for every difficulty tier.
    """

    info("\n================ PERFORMANCE BY DIFFICULTY ================")

    info(
        f"{'Model / Difficulty':<36} | "
        f"{'N':>4} | "
        f"{'SR':>7} | "
        f"{'P@1':>7} | "
        f"{'TTR':>9} | "
        f"{'IE':>7} | "
        f"{'ARI':>7} | "
        f"{'FR':>7}"
    )

    info("-" * 106)

    for model, statistics in aggregates.items():
        difficulty_statistics = statistics["difficulties"]

        ordered_difficulties = sorted(
            difficulty_statistics,
            key=lambda difficulty: DIFFICULTY_LEVELS[difficulty]["tier"],
        )

        for difficulty in ordered_difficulties:
            metadata = DIFFICULTY_LEVELS[difficulty]

            label = f"{model} / {metadata['code']} {metadata['label']}"

            display_metric_line(
                label=label,
                statistics=(difficulty_statistics[difficulty]),
            )

    info("=" * 106)


def display_failure_analysis(
    aggregates: dict[str, dict[str, Any]],
) -> None:
    """
    Display failure-reason counts.
    """

    info("\n================ FAILURE ANALYSIS =================")

    for model, statistics in aggregates.items():
        info(f"\nModel: {model}")

        reasons = statistics["failure_reasons"]

        if not reasons:
            success("No failures recorded.")
            continue

        ordered_reasons = sorted(
            reasons.items(),
            key=lambda item: (
                -item[1],
                item[0],
            ),
        )

        for reason, count in ordered_reasons:
            suffix = "" if count == 1 else "s"

            info(f"  - {reason}: {count} occurrence{suffix}")

    info("=" * 53)


def log_breakdown_statistics(
    aggregates: dict[str, dict[str, Any]],
) -> None:
    """
    Write category and difficulty statistics to execution.log.
    """

    logging.info("================ DIFFICULTY PERFORMANCE ================")

    for model, statistics in aggregates.items():
        logging.info(
            "Model: %s",
            model,
        )

        for difficulty, bucket in sorted(
            statistics["difficulties"].items(),
            key=lambda item: DIFFICULTY_LEVELS[item[0]]["tier"],
        ):
            metrics = calculate_metrics(bucket)

            metadata = DIFFICULTY_LEVELS[difficulty]

            logging.info(
                (
                    "Difficulty=%s | "
                    "Tier=%s | "
                    "Label=%s | "
                    "Attempts=%d | "
                    "Success=%d | "
                    "SR=%.2f%% | "
                    "P@1=%.2f%% | "
                    "MeanTTR=%s | "
                    "IE=%s | "
                    "ARI=%s"
                ),
                difficulty,
                metadata["code"],
                metadata["label"],
                bucket["attempts"],
                bucket["success"],
                metrics["success_rate"],
                metrics["pass_at_1"],
                (f"{metrics['mean_ttr']:.3f}s" if bucket["success"] else "N/A"),
                (
                    f"{metrics['iteration_efficiency']:.3f}"
                    if bucket["success"]
                    else "N/A"
                ),
                (
                    f"{metrics['average_iterations']:.3f}"
                    if bucket["success"]
                    else "N/A"
                ),
            )

    logging.info("================ CATEGORY PERFORMANCE ================")

    for model, statistics in aggregates.items():
        logging.info(
            "Model: %s",
            model,
        )

        for combined_key, bucket in sorted(statistics["difficulty_categories"].items()):
            metrics = calculate_metrics(bucket)

            logging.info(
                (
                    "DifficultyCategory=%s | "
                    "Attempts=%d | "
                    "Success=%d | "
                    "SR=%.2f%% | "
                    "MeanTTR=%s"
                ),
                combined_key,
                bucket["attempts"],
                bucket["success"],
                metrics["success_rate"],
                (f"{metrics['mean_ttr']:.3f}s" if bucket["success"] else "N/A"),
            )


# =========================================================
# Main Evaluation Pipeline
# =========================================================


def run_evaluation_pipeline() -> None:
    """
    Run the selected benchmark experiment.
    """

    parser = create_parser()
    args = parser.parse_args()

    if args.max_iterations < 1:
        parser.error("--max-iterations must be at least 1.")

    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero.")

    project_root = os.path.abspath(os.path.dirname(__file__))

    models_to_test = list(args.models) if args.models else list(AVAILABLE_MODELS)

    selected_categories = list(args.types) if args.types else None

    selected_difficulties = list(args.difficulties) if args.difficulties else None

    if args.git_reset_benchmarks:
        restore_committed_benchmarks(project_root)

    run_dir = setup_logging(
        models=models_to_test,
        categories=selected_categories,
        difficulties=selected_difficulties,
    )

    experiment_start = time.perf_counter()

    info("=" * 80)
    info("CLEAR MULTI-MODEL BENCHMARK EXPERIMENT")
    info("=" * 80)

    info(f"Experiment type: {EXPERIMENT_TYPE}")

    info(f"Models: {models_to_test}")

    info(f"Difficulty levels: {selected_difficulties or 'All'}")

    info(f"Categories: {selected_categories or 'All'}")

    info(f"Maximum repair iterations: {args.max_iterations}")

    info(f"Per-benchmark timeout: {args.timeout:.1f}s")

    info(f"Python executable: {sys.executable}")

    info(f"Python version: {sys.version.split()[0]}")

    info(f"Run directory: {run_dir}")

    info("=" * 80)

    logging.info(
        "Experiment started at %s",
        datetime.now().isoformat(),
    )

    benchmarks_dir = os.path.join(
        project_root,
        "tests",
        "benchmarks",
    )

    benchmark_tasks = discover_benchmarks(
        benchmarks_dir=benchmarks_dir,
        selected_categories=(selected_categories),
        selected_difficulties=(selected_difficulties),
    )

    if not benchmark_tasks:
        failure("No matching benchmark tasks were discovered.")
        raise SystemExit(1)

    counts_by_difficulty = Counter(task["difficulty"] for task in benchmark_tasks)

    info(f"Discovered {len(benchmark_tasks)} benchmark cases.")

    for difficulty in AVAILABLE_DIFFICULTIES:
        count = counts_by_difficulty.get(
            difficulty,
            0,
        )

        if count:
            metadata = DIFFICULTY_LEVELS[difficulty]

            info(f"  {metadata['code']} {metadata['label']}: {count}")

    aggregates = initialise_model_aggregates(models_to_test)

    raw_execution_data: list[dict[str, Any]] = []

    catastrophic_errors = 0

    # =====================================================
    # Sequential Evaluation
    # =====================================================

    for model in models_to_test:
        info(f"\nEvaluating model: {model}")

        info("=" * 80)

        current_group: tuple[str, str] | None = None

        for task in benchmark_tasks:
            group = (
                task["difficulty"],
                task["category_name"],
            )

            if group != current_group:
                info(
                    "\n--- "
                    f"{task['difficulty_code']} | "
                    f"{task['difficulty_label'].upper()} | "
                    f"{task['category_name'].upper()} "
                    "---"
                )

                current_group = group

            try:
                result = execute_benchmark(
                    model=model,
                    task=task,
                    project_root=project_root,
                    timeout_seconds=(args.timeout),
                    max_iterations=(args.max_iterations),
                )

            except Exception as exc:
                catastrophic_errors += 1

                result = {
                    "model": model,
                    "difficulty": (task["difficulty"]),
                    "difficulty_tier": (task["difficulty_tier"]),
                    "difficulty_code": (task["difficulty_code"]),
                    "difficulty_label": (task["difficulty_label"]),
                    "difficulty_definition": (task["difficulty_definition"]),
                    "category": (task["category_name"]),
                    "benchmark": (task["benchmark_name"]),
                    "benchmark_id": (task["benchmark_id"]),
                    "passed": False,
                    "verified": False,
                    "ttr": 0.0,
                    "wall_time": 0.0,
                    "iterations": 0,
                    "failure_reason": (
                        f"Benchmark runner crash: {type(exc).__name__}: {exc}"
                    ),
                    "return_code": None,
                    "timed_out": False,
                }

                logging.exception(
                    "Catastrophic runner error for %s.",
                    task["benchmark_id"],
                )

                if args.stop_on_error:
                    raw_execution_data.append(result)

                    update_aggregates(
                        aggregates=aggregates,
                        result=result,
                    )

                    display_benchmark_result(result)

                    export_results(
                        raw_execution_data,
                        run_dir,
                    )

                    raise

            raw_execution_data.append(result)

            update_aggregates(
                aggregates=aggregates,
                result=result,
            )

            display_benchmark_result(result)

    # =====================================================
    # Final Reporting
    # =====================================================

    display_final_performance_matrix(aggregates)

    display_difficulty_performance(aggregates)

    display_failure_analysis(aggregates)

    log_breakdown_statistics(aggregates)

    export_results(
        raw_execution_data,
        run_dir,
    )

    experiment_duration = time.perf_counter() - experiment_start

    info("\nBenchmark evaluation completed.")

    info(f"Total experiment duration: {experiment_duration:.2f}s")

    info(f"Catastrophic runner errors: {catastrophic_errors}")

    info(f"Outputs saved to: {run_dir}")

    info("=" * 80)

    logging.info(
        "Experiment completed at %s",
        datetime.now().isoformat(),
    )

    logging.info(
        "Total duration: %.3f seconds",
        experiment_duration,
    )

    if catastrophic_errors > 0:
        raise SystemExit(2)


# =========================================================
# Program Entry Point
# =========================================================


if __name__ == "__main__":
    run_evaluation_pipeline()
