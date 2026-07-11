"""Markdown report generation for CLEAR benchmark experiments."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from src.benchmarking.difficulty import ordered_difficulties
from src.benchmarking.models import BenchmarkResult, ExperimentSettings
from src.reporting.tables import markdown_table


MODEL_COLUMNS = [
    ("model", "Model"),
    ("attempts", "N"),
    ("success_rate_pct", "SR (%)"),
    ("pass_at_1_pct", "Pass@1 (%)"),
    ("mean_ttr_s", "TTR (s)"),
    ("iteration_efficiency", "IE"),
    ("average_repair_iterations", "ARI"),
    ("failure_rate_pct", "FR (%)"),
]

DIFFICULTY_COLUMNS = [
    ("difficulty_tier", "Tier"),
    ("difficulty_label", "Difficulty"),
    ("attempts", "N"),
    ("success_rate_pct", "SR (%)"),
    ("pass_at_1_pct", "Pass@1 (%)"),
    ("mean_ttr_s", "TTR (s)"),
    ("average_repair_iterations", "ARI"),
    ("failure_rate_pct", "FR (%)"),
]

MODEL_DIFFICULTY_COLUMNS = [
    ("model", "Model"),
    ("difficulty_tier", "Tier"),
    ("difficulty_label", "Difficulty"),
    ("attempts", "N"),
    ("success_rate_pct", "SR (%)"),
    ("pass_at_1_pct", "Pass@1 (%)"),
    ("mean_ttr_s", "TTR (s)"),
    ("iteration_efficiency", "IE"),
    ("average_repair_iterations", "ARI"),
    ("failure_rate_pct", "FR (%)"),
]

FAILURE_COLUMNS = [
    ("model", "Model"),
    ("difficulty_tier", "Tier"),
    ("difficulty_label", "Difficulty"),
    ("failure_reason", "Failure reason"),
    ("count", "Count"),
]


def _difficulty_definition_table() -> str:
    """Return the canonical dissertation difficulty table."""

    rows = [
        {
            "tier": f"Tier {difficulty.tier}",
            "folder": f"`{difficulty.name}`",
            "label": difficulty.label,
            "definition": difficulty.definition,
        }
        for difficulty in ordered_difficulties()
    ]

    return markdown_table(
        rows,
        [
            ("tier", "Tier"),
            ("folder", "Folder"),
            ("label", "Dissertation label"),
            ("definition", "Definition"),
        ],
    )


def write_analysis_report(
    *,
    destination: str | Path,
    results: list[BenchmarkResult],
    settings: ExperimentSettings,
    summary_by_model: list[dict[str, Any]],
    summary_by_difficulty: list[dict[str, Any]],
    summary_by_model_difficulty: list[dict[str, Any]],
    failure_summary: list[dict[str, Any]],
) -> None:
    """Write the human-readable experiment summary report."""

    output_path = Path(destination)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    models = sorted({result.model for result in results})
    categories = sorted({result.category for result in results})
    difficulties = sorted(
        {result.difficulty for result in results},
        key=lambda name: next(
            item.tier for item in ordered_difficulties() if item.name == name
        ),
    )
    benchmarks = {result.benchmark_id for result in results}

    failures_section = (
        markdown_table(failure_summary, FAILURE_COLUMNS)
        if failure_summary
        else "No failures were recorded."
    )

    report = f"""# CLEAR Benchmark Experiment Report

Generated: {datetime.now().isoformat()}

## Experiment Configuration

- Models: {', '.join(settings.models)}
- Selected categories: {', '.join(settings.categories) if settings.categories else 'All'}
- Selected difficulty levels: {', '.join(settings.difficulties) if settings.difficulties else 'All'}
- Maximum repair iterations: {settings.max_iterations}
- Per-benchmark timeout: {settings.timeout_seconds:.1f} seconds

## Dataset Overview

- Repair attempts: {len(results)}
- Models represented: {len(models)}
- Difficulty levels represented: {len(difficulties)}
- Categories represented: {len(categories)}
- Unique benchmark cases: {len(benchmarks)}

## Difficulty Definitions

{_difficulty_definition_table()}

## Overall Model Performance

{markdown_table(summary_by_model, MODEL_COLUMNS)}

## Performance by Difficulty

{markdown_table(summary_by_difficulty, DIFFICULTY_COLUMNS)}

## Model × Difficulty Performance

{markdown_table(summary_by_model_difficulty, MODEL_DIFFICULTY_COLUMNS)}

## Failure Analysis

{failures_section}

## Metric Interpretation

- **Success Rate (SR):** percentage of attempted benchmarks that produced a verified repair.
- **Pass@1:** percentage of all attempted benchmarks repaired in exactly one repair attempt.
- **Time to Resolution (TTR):** mean successful repair time in seconds.
- **Iteration Efficiency (IE):** mean reciprocal repair-attempt count across successful repairs.
- **Average Repair Iterations (ARI):** mean number of attempts across successful repairs.
- **Failure Rate (FR):** percentage of attempted benchmarks that did not produce a verified repair.
"""

    output_path.write_text(report, encoding="utf-8")
