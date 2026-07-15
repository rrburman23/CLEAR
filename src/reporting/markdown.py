"""Markdown report generation for CLEAR benchmark experiments."""

from __future__ import annotations

from datetime import datetime, timezone
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

CATEGORY_COLUMNS = [
    ("category", "Category"),
    ("attempts", "N"),
    ("success_rate_pct", "SR (%)"),
    ("pass_at_1_pct", "Pass@1 (%)"),
    ("mean_ttr_s", "TTR (s)"),
    ("average_repair_iterations", "ARI"),
    ("failure_rate_pct", "FR (%)"),
]

FAILURE_COLUMNS = [
    ("failure_reason", "Failure reason"),
    ("count", "Count"),
    ("share_of_failures_pct", "Share of failures (%)"),
]

FAILURE_BY_MODEL_COLUMNS = [
    ("model", "Model"),
    ("failure_reason", "Failure reason"),
    ("count", "Count"),
    ("share_of_model_failures_pct", "Share within model failures (%)"),
]

HARDEST_BENCHMARK_COLUMNS = [
    ("difficulty", "Difficulty"),
    ("category", "Category"),
    ("benchmark", "Benchmark"),
    ("attempts", "N"),
    ("success_rate_pct", "SR (%)"),
    ("most_common_failure_reason", "Most common failure"),
]

PASS_AT_K_COLUMNS = [
    ("model", "Model"),
    ("attempts", "N"),
    ("pass_at_1_pct", "Pass@1 (%)"),
    ("pass_at_2_pct", "Pass@2 (%)"),
    ("pass_at_3_pct", "Pass@3 (%)"),
    ("pass_at_5_pct", "Pass@5 (%)"),
]


def _difficulty_definition_table() -> str:
    rows = [
        {
            "tier": f"T{difficulty.tier}",
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


def _safe_table(
    rows: list[dict[str, Any]], columns: list[tuple[str, str]], empty: str
) -> str:
    return markdown_table(rows, columns) if rows else empty


def _kpi_block(summary_by_model: list[dict[str, Any]]) -> str:
    if not summary_by_model:
        return "- No model summary rows available."

    best_sr = max(summary_by_model, key=lambda row: row.get("success_rate_pct", -1))
    best_p1 = max(summary_by_model, key=lambda row: row.get("pass_at_1_pct", -1))
    best_ttr_candidates = [
        row for row in summary_by_model if row.get("mean_ttr_s") is not None
    ]
    best_ttr = (
        min(best_ttr_candidates, key=lambda row: row.get("mean_ttr_s", 10**9))
        if best_ttr_candidates
        else None
    )

    lines = [
        f"- Best **Success Rate**: `{best_sr.get('model', 'N/A')}` ({best_sr.get('success_rate_pct', 0):.1f}%)",
        f"- Best **Pass@1**: `{best_p1.get('model', 'N/A')}` ({best_p1.get('pass_at_1_pct', 0):.1f}%)",
    ]
    if best_ttr:
        lines.append(
            f"- Fastest mean successful-repair **TTR**: `{best_ttr.get('model', 'N/A')}` ({best_ttr.get('mean_ttr_s', 0):.2f} s)"
        )
    return "\n".join(lines)


def write_analysis_report(
    *,
    destination: str | Path,
    results: list[BenchmarkResult],
    settings: ExperimentSettings,
    summary_by_model: list[dict[str, Any]],
    summary_by_difficulty: list[dict[str, Any]],
    summary_by_model_difficulty: list[dict[str, Any]],
    failure_summary: list[dict[str, Any]],
    summary_by_category: list[dict[str, Any]] | None = None,
    failures_by_model: list[dict[str, Any]] | None = None,
    hardest_benchmarks: list[dict[str, Any]] | None = None,
    pass_at_k_summary: list[dict[str, Any]] | None = None,
) -> None:
    """Write the human-readable experiment summary report."""

    output_path = Path(destination)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    summary_by_category = summary_by_category or []
    failures_by_model = failures_by_model or []
    hardest_benchmarks = hardest_benchmarks or []
    pass_at_k_summary = pass_at_k_summary or []

    models = sorted({result.model for result in results})
    categories = sorted({result.category for result in results})
    difficulties = sorted(
        {result.difficulty for result in results},
        key=lambda name: next(
            (item.tier for item in ordered_difficulties() if item.name == name),
            999,
        ),
    )
    benchmarks = {result.benchmark_id for result in results}

    generated_at = datetime.now(timezone.utc).isoformat()

    report = f"""# CLEAR Benchmark Experiment Report

Generated (UTC): {generated_at}

## 1) Experiment Configuration

- Models: {", ".join(settings.models)}
- Selected categories: {", ".join(settings.categories) if settings.categories else "All"}
- Selected difficulty levels: {", ".join(settings.difficulties) if settings.difficulties else "All"}
- Maximum repair iterations: {settings.max_iterations}
- Per-benchmark timeout: {settings.timeout_seconds:.1f} seconds

## 2) Dataset Overview

- Total repair attempts: {len(results)}
- Models represented: {len(models)}
- Difficulty levels represented: {len(difficulties)}
- Categories represented: {len(categories)}
- Unique benchmark cases: {len(benchmarks)}

## 3) At-a-Glance KPIs

{_kpi_block(summary_by_model)}

## 4) Difficulty Definitions

{_difficulty_definition_table()}

## 5) Overall Model Performance

{_safe_table(summary_by_model, MODEL_COLUMNS, "No model summary available.")}

## 6) Performance by Difficulty

{_safe_table(summary_by_difficulty, DIFFICULTY_COLUMNS, "No difficulty summary available.")}

## 7) Model × Difficulty Performance

{_safe_table(summary_by_model_difficulty, MODEL_DIFFICULTY_COLUMNS, "No model × difficulty summary available.")}

## 8) Performance by Category

{_safe_table(summary_by_category, CATEGORY_COLUMNS, "No category summary available.")}

## 9) Pass@k Summary

{_safe_table(pass_at_k_summary, PASS_AT_K_COLUMNS, "No Pass@k summary available.")}

## 10) Failure Analysis (Global)

{_safe_table(failure_summary, FAILURE_COLUMNS, "No failures were recorded.")}

## 11) Failure Analysis by Model

{_safe_table(failures_by_model, FAILURE_BY_MODEL_COLUMNS, "No model-specific failures were recorded.")}

## 12) Hardest Benchmarks

{_safe_table(hardest_benchmarks, HARDEST_BENCHMARK_COLUMNS, "No hardest-benchmark data available.")}

## 13) Metric Interpretation

- **Success Rate (SR):** percentage of attempted benchmarks that produced a verified repair.
- **Pass@1:** percentage of all attempted benchmarks repaired in exactly one repair attempt.
- **Time to Resolution (TTR):** mean successful repair time in seconds.
- **Iteration Efficiency (IE):** mean reciprocal repair-attempt count across successful repairs.
- **Average Repair Iterations (ARI):** mean number of attempts across successful repairs.
- **Failure Rate (FR):** percentage of attempted benchmarks that did not produce a verified repair.
"""

    output_path.write_text(report, encoding="utf-8")
