"""Command-line parsing for CLEAR benchmark experiments."""

from __future__ import annotations

import argparse

from src.utils.config import (
    AVAILABLE_MODELS,
    AVAILABLE_TYPES,
    DEFAULT_BENCHMARK_TIMEOUT,
    DEFAULT_MAX_ITERATIONS,
)
from src.benchmarking.difficulty import AVAILABLE_DIFFICULTIES, ordered_difficulties
from src.benchmarking.models import ExperimentSettings


def create_parser() -> argparse.ArgumentParser:
    """Build and return the public benchmark CLI parser."""

    model_block = "\n".join(f"  - {model}" for model in AVAILABLE_MODELS)
    difficulty_block = "\n".join(
        f"  - {item.name}: Tier {item.tier} — {item.label}"
        for item in ordered_difficulties()
    )

    parser = argparse.ArgumentParser(
        prog="CLEAR Benchmark Runner",
        description=(
            "Evaluate local language models on the CLEAR autonomous "
            "program-repair benchmark."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available models:
{model_block}

Difficulty levels:
{difficulty_block}

Examples:

  Run every configured model and benchmark:
      python -m run_benchmarks

  Run one model:
      python -m run_benchmarks --models codegemma:7b

  Run Tier 1 only:
      python -m run_benchmarks --difficulties single_fault

  Run Tier 2 and Tier 3:
      python -m run_benchmarks --difficulties compound_same_category compound_cross_category

  Restrict the experiment to selected fault categories:
      python -m run_benchmarks --types logic syntax security

  Combine model, tier, and category filters:
      python -m run_benchmarks --models codegemma:7b --difficulties single_fault --types logic

  Allow ten minutes per benchmark subprocess:
      python -m run_benchmarks --timeout 600
""",
    )

    parser.add_argument(
        "--models",
        nargs="+",
        choices=AVAILABLE_MODELS,
        metavar="MODEL",
        help=(
            "Models to evaluate. If omitted, every configured model is "
            "evaluated sequentially."
        ),
    )

    parser.add_argument(
        "--types",
        nargs="+",
        choices=AVAILABLE_TYPES,
        metavar="TYPE",
        help=(
            "Fault categories to evaluate. If omitted, all discovered "
            "categories are evaluated."
        ),
    )

    parser.add_argument(
        "--difficulties",
        "--tiers",
        dest="difficulties",
        nargs="+",
        choices=AVAILABLE_DIFFICULTIES,
        metavar="DIFFICULTY",
        help=(
            "Difficulty levels to evaluate. If omitted, every discovered "
            "difficulty level is evaluated."
        ),
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
            "Maximum wall-clock duration for each benchmark subprocess. "
            f"Default: {DEFAULT_BENCHMARK_TIMEOUT:.0f} seconds."
        ),
    )

    parser.add_argument(
        "--git-reset-benchmarks",
        action="store_true",
        help=(
            "Run 'git restore tests/benchmarks' before evaluation. This "
            "discards uncommitted changes under that directory."
        ),
    )

    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help=(
            "Stop the full experiment after a catastrophic benchmark-runner "
            "error. Normal model repair failures do not stop execution."
        ),
    )

    return parser


def parse_settings() -> ExperimentSettings:
    """Parse, validate, and normalise public CLI arguments."""

    parser = create_parser()
    arguments = parser.parse_args()

    if arguments.max_iterations < 1:
        parser.error("--max-iterations must be at least 1.")

    if arguments.timeout <= 0:
        parser.error("--timeout must be greater than zero.")

    return ExperimentSettings(
        models=(
            list(arguments.models)
            if arguments.models
            else list(AVAILABLE_MODELS)
        ),
        categories=(list(arguments.types) if arguments.types else None),
        difficulties=(
            list(arguments.difficulties) if arguments.difficulties else None
        ),
        max_iterations=arguments.max_iterations,
        timeout_seconds=arguments.timeout,
        git_reset_benchmarks=arguments.git_reset_benchmarks,
        stop_on_error=arguments.stop_on_error,
    )
