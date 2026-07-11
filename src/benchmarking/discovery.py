"""Filesystem discovery for CLEAR benchmark cases."""

from __future__ import annotations

import logging
from pathlib import Path

from src.benchmarking.difficulty import DIFFICULTIES, get_difficulty
from src.benchmarking.models import BenchmarkTask


def infer_benchmark_location(
    benchmark_directory: Path,
    benchmarks_root: Path,
) -> tuple[str, str, str] | None:
    """Infer difficulty, category, and benchmark name from a path.

    Supported tiered layout::

        benchmarks/<difficulty>/<category>/<benchmark>/

    Supported legacy layout::

        benchmarks/<category>/<benchmark>/

    Legacy benchmarks are treated as Tier 1 ``single_fault`` cases so the
    existing dataset can be migrated incrementally.
    """

    relative = benchmark_directory.relative_to(benchmarks_root)
    parts = relative.parts

    if not parts:
        return None

    if parts[0] in DIFFICULTIES:
        if len(parts) < 3:
            return None

        return parts[0], parts[1], parts[-1]

    if len(parts) < 2:
        return None

    return "single_fault", parts[0], parts[-1]


def select_test_file(
    benchmark_directory: Path,
) -> Path | None:
    """Return the deterministic test oracle for a benchmark directory."""

    candidates = sorted(benchmark_directory.glob("test_*.py"))

    if not candidates:
        return None

    if len(candidates) > 1:
        logging.warning(
            "Multiple test files found for %s. Using %s.",
            benchmark_directory,
            candidates[0].name,
        )

    return candidates[0]


def discover_benchmarks(
    benchmarks_dir: str | Path,
    selected_categories: list[str] | None = None,
    selected_difficulties: list[str] | None = None,
) -> list[BenchmarkTask]:
    """Discover, filter, and sort benchmark cases.

    Only directories containing both ``target.py`` and at least one
    ``test_*.py`` file are returned.
    """

    root = Path(benchmarks_dir).resolve()

    if not root.exists():
        raise FileNotFoundError(f"Benchmark directory does not exist: {root}")

    tasks: list[BenchmarkTask] = []

    for target_file in root.rglob("target.py"):
        benchmark_directory = target_file.parent
        location = infer_benchmark_location(benchmark_directory, root)

        if location is None:
            logging.warning(
                "Unable to infer benchmark metadata for %s.",
                benchmark_directory,
            )
            continue

        difficulty_name, category, benchmark = location

        if (
            selected_difficulties
            and difficulty_name not in selected_difficulties
        ):
            continue

        if selected_categories and category not in selected_categories:
            continue

        test_file = select_test_file(benchmark_directory)

        if test_file is None:
            logging.warning("No test oracle found for %s.", target_file)
            continue

        tasks.append(
            BenchmarkTask(
                difficulty=get_difficulty(difficulty_name),
                category=category,
                benchmark=benchmark,
                root=str(benchmark_directory),
                target_file=str(target_file),
                test_file=str(test_file),
            )
        )

    tasks.sort(
        key=lambda task: (
            task.difficulty.tier,
            task.category,
            task.benchmark,
        )
    )

    return tasks
