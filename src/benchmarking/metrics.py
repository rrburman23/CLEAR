"""Metric calculation and grouping for CLEAR benchmark results."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

from src.benchmarking.models import BenchmarkResult, MetricSummary


def _mean(values: Iterable[float]) -> float | None:
    """Return the arithmetic mean, or ``None`` for an empty sequence."""

    materialised = list(values)

    if not materialised:
        return None

    return sum(materialised) / len(materialised)


def calculate_summary(results: list[BenchmarkResult]) -> MetricSummary:
    """Calculate the primary CLEAR metrics for a result collection.

    Success Rate, Pass@1, and Failure Rate use all attempted benchmarks.
    TTR, Iteration Efficiency, and Average Repair Iterations use verified
    successful repairs only, matching the dissertation metric definitions.
    """

    attempts = len(results)
    successful = [result for result in results if result.passed]
    successes = len(successful)
    failures = attempts - successes

    pass_at_1_count = sum(result.iterations == 1 for result in successful)

    return MetricSummary(
        attempts=attempts,
        successes=successes,
        failures=failures,
        success_rate_pct=(100 * successes / attempts if attempts else 0.0),
        pass_at_1_pct=(100 * pass_at_1_count / attempts if attempts else 0.0),
        mean_ttr_s=_mean(result.ttr for result in successful),
        mean_wall_time_s=_mean(result.wall_time for result in successful),
        iteration_efficiency=_mean(
            1 / result.iterations
            for result in successful
            if result.iterations > 0
        ),
        average_repair_iterations=_mean(
            float(result.iterations) for result in successful
        ),
        failure_rate_pct=(100 * failures / attempts if attempts else 0.0),
    )


def group_results(
    results: list[BenchmarkResult],
    *attributes: str,
) -> dict[tuple[Any, ...], list[BenchmarkResult]]:
    """Group results by one or more dataclass attribute names."""

    grouped: dict[tuple[Any, ...], list[BenchmarkResult]] = defaultdict(list)

    for result in results:
        key = tuple(getattr(result, attribute) for attribute in attributes)
        grouped[key].append(result)

    return dict(grouped)


def summarise_by(
    results: list[BenchmarkResult],
    *attributes: str,
) -> list[dict[str, Any]]:
    """Return serialisable metric rows grouped by ``attributes``."""

    rows: list[dict[str, Any]] = []

    for key, grouped_results in group_results(results, *attributes).items():
        row = {
            attribute: value
            for attribute, value in zip(attributes, key, strict=True)
        }
        row.update(calculate_summary(grouped_results).to_dict())
        rows.append(row)

    rows.sort(key=lambda row: tuple(str(row[field]) for field in attributes))
    return rows


def summarise_by_model(
    results: list[BenchmarkResult],
) -> list[dict[str, Any]]:
    """Return one aggregate metric row per model."""

    return summarise_by(results, "model")


def summarise_by_difficulty(
    results: list[BenchmarkResult],
) -> list[dict[str, Any]]:
    """Return one aggregate metric row per difficulty level."""

    rows = summarise_by(results, "difficulty", "difficulty_tier", "difficulty_label")
    rows.sort(key=lambda row: int(row["difficulty_tier"]))
    return rows


def summarise_by_category(
    results: list[BenchmarkResult],
) -> list[dict[str, Any]]:
    """Return one aggregate metric row per fault category."""

    return summarise_by(results, "category")


def summarise_by_model_difficulty(
    results: list[BenchmarkResult],
) -> list[dict[str, Any]]:
    """Return model-by-difficulty aggregate metrics."""

    rows = summarise_by(
        results,
        "model",
        "difficulty",
        "difficulty_tier",
        "difficulty_label",
    )
    rows.sort(key=lambda row: (str(row["model"]), int(row["difficulty_tier"])))
    return rows


def summarise_by_model_category(
    results: list[BenchmarkResult],
) -> list[dict[str, Any]]:
    """Return model-by-category aggregate metrics."""

    return summarise_by(results, "model", "category")


def summarise_by_difficulty_category(
    results: list[BenchmarkResult],
) -> list[dict[str, Any]]:
    """Return difficulty-by-category aggregate metrics."""

    rows = summarise_by(
        results,
        "difficulty",
        "difficulty_tier",
        "difficulty_label",
        "category",
    )
    rows.sort(key=lambda row: (int(row["difficulty_tier"]), str(row["category"])))
    return rows


def build_failure_summary(
    results: list[BenchmarkResult],
) -> list[dict[str, Any]]:
    """Count failure reasons by model and difficulty level."""

    counts: dict[tuple[str, str, int, str, str], int] = defaultdict(int)

    for result in results:
        if result.passed:
            continue

        reason = result.failure_reason or "Unknown repair failure"
        key = (
            result.model,
            result.difficulty,
            result.difficulty_tier,
            result.difficulty_label,
            reason,
        )
        counts[key] += 1

    rows = [
        {
            "model": model,
            "difficulty": difficulty,
            "difficulty_tier": tier,
            "difficulty_label": label,
            "failure_reason": reason,
            "count": count,
        }
        for (model, difficulty, tier, label, reason), count in counts.items()
    ]

    rows.sort(
        key=lambda row: (
            str(row["model"]),
            int(row["difficulty_tier"]),
            -int(row["count"]),
            str(row["failure_reason"]),
        )
    )

    return rows
