"""High-level export orchestration for CLEAR benchmark experiments."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from src.benchmarking.constants import DATASET_FIELDS
from src.benchmarking.difficulty import ordered_difficulties
from src.benchmarking.metrics import (
    build_failure_summary,
    summarise_by_category,
    summarise_by_difficulty,
    summarise_by_difficulty_category,
    summarise_by_model,
    summarise_by_model_category,
    summarise_by_model_difficulty,
)
from src.benchmarking.models import BenchmarkResult, ExperimentSettings
from src.reporting.graphs import generate_graphs
from src.reporting.markdown import (
    DIFFICULTY_COLUMNS,
    MODEL_COLUMNS,
    MODEL_DIFFICULTY_COLUMNS,
    write_analysis_report,
)
from src.reporting.tables import write_csv, write_latex_table
from src.utils.terminal import success, warning


FAILURE_COLUMNS = [
    ("model", "Model"),
    ("difficulty_tier", "Tier"),
    ("difficulty_label", "Difficulty"),
    ("failure_reason", "Failure reason"),
    ("count", "Count"),
]

CATEGORY_COLUMNS = [
    ("category", "Category"),
    ("attempts", "N"),
    ("success_rate_pct", "SR (percent)"),
    ("pass_at_1_pct", "Pass@1 (percent)"),
    ("mean_ttr_s", "TTR (s)"),
    ("average_repair_iterations", "ARI"),
    ("failure_rate_pct", "FR (percent)"),
]


def _difficulty_definitions() -> dict[str, dict[str, Any]]:
    """Return canonical tier metadata for JSON export."""

    return {
        item.name: {
            "tier": item.tier,
            "code": item.code,
            "label": item.label,
            "definition": item.definition,
        }
        for item in ordered_difficulties()
    }


def _write_json_dataset(
    destination: Path,
    *,
    settings: ExperimentSettings,
    records: list[dict[str, Any]],
    summaries: dict[str, list[dict[str, Any]]],
) -> None:
    """Write raw results and every aggregate table to one JSON document."""

    payload = {
        "schema_version": "3.0",
        "generated_at": datetime.now().isoformat(),
        "experiment_settings": settings.to_dict(),
        "difficulty_definitions": _difficulty_definitions(),
        "records": records,
        **summaries,
    }

    destination.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _write_latex_tables(
    tables_directory: Path,
    *,
    summary_by_model: list[dict[str, Any]],
    summary_by_difficulty: list[dict[str, Any]],
    summary_by_model_difficulty: list[dict[str, Any]],
    summary_by_category: list[dict[str, Any]],
    failure_summary: list[dict[str, Any]],
) -> None:
    """Write dissertation-ready LaTeX versions of the main summary tables."""

    write_latex_table(
        tables_directory / "summary_by_model.tex",
        summary_by_model,
        MODEL_COLUMNS,
        caption="CLEAR performance by model",
        label="tab:clear-model-performance",
    )

    write_latex_table(
        tables_directory / "summary_by_difficulty.tex",
        summary_by_difficulty,
        DIFFICULTY_COLUMNS,
        caption="CLEAR performance by benchmark difficulty",
        label="tab:clear-difficulty-performance",
    )

    write_latex_table(
        tables_directory / "summary_by_model_difficulty.tex",
        summary_by_model_difficulty,
        MODEL_DIFFICULTY_COLUMNS,
        caption="CLEAR model performance by benchmark difficulty",
        label="tab:clear-model-difficulty-performance",
    )

    write_latex_table(
        tables_directory / "summary_by_category.tex",
        summary_by_category,
        CATEGORY_COLUMNS,
        caption="CLEAR performance by fault category",
        label="tab:clear-category-performance",
    )

    if failure_summary:
        write_latex_table(
            tables_directory / "failure_summary.tex",
            failure_summary,
            FAILURE_COLUMNS,
            caption="CLEAR failure taxonomy by model and difficulty",
            label="tab:clear-failure-summary",
        )


def export_experiment(
    results: list[BenchmarkResult],
    run_directory: str | Path,
    settings: ExperimentSettings,
) -> None:
    """Export raw data, summaries, report, LaTeX tables, and figures."""

    run_dir = Path(run_directory)
    run_dir.mkdir(parents=True, exist_ok=True)

    tables_dir = run_dir / "tables"
    graphs_dir = run_dir / "graphs"
    tables_dir.mkdir(parents=True, exist_ok=True)
    graphs_dir.mkdir(parents=True, exist_ok=True)

    records = [result.to_dict() for result in results]

    summary_by_model = summarise_by_model(results)
    summary_by_difficulty = summarise_by_difficulty(results)
    summary_by_category = summarise_by_category(results)
    summary_by_model_difficulty = summarise_by_model_difficulty(results)
    summary_by_model_category = summarise_by_model_category(results)
    summary_by_difficulty_category = summarise_by_difficulty_category(results)
    failure_summary = build_failure_summary(results)

    summaries = {
        "summary_by_model": summary_by_model,
        "summary_by_difficulty": summary_by_difficulty,
        "summary_by_category": summary_by_category,
        "summary_by_model_difficulty": summary_by_model_difficulty,
        "summary_by_model_category": summary_by_model_category,
        "summary_by_difficulty_category": summary_by_difficulty_category,
        "failure_summary": failure_summary,
    }

    write_csv(run_dir / "dataset.csv", records, DATASET_FIELDS)
    write_csv(tables_dir / "summary_by_model.csv", summary_by_model)
    write_csv(tables_dir / "summary_by_difficulty.csv", summary_by_difficulty)
    write_csv(tables_dir / "summary_by_category.csv", summary_by_category)
    write_csv(
        tables_dir / "summary_by_model_difficulty.csv",
        summary_by_model_difficulty,
    )
    write_csv(
        tables_dir / "summary_by_model_category.csv",
        summary_by_model_category,
    )
    write_csv(
        tables_dir / "summary_by_difficulty_category.csv",
        summary_by_difficulty_category,
    )
    write_csv(
        tables_dir / "failure_summary.csv",
        failure_summary,
        [
            "model",
            "difficulty",
            "difficulty_tier",
            "difficulty_label",
            "failure_reason",
            "count",
        ],
    )

    _write_json_dataset(
        run_dir / "dataset.json",
        settings=settings,
        records=records,
        summaries=summaries,
    )

    write_analysis_report(
        destination=run_dir / "analysis_report.md",
        results=results,
        settings=settings,
        summary_by_model=summary_by_model,
        summary_by_difficulty=summary_by_difficulty,
        summary_by_model_difficulty=summary_by_model_difficulty,
        failure_summary=failure_summary,
    )

    _write_latex_tables(
        tables_dir,
        summary_by_model=summary_by_model,
        summary_by_difficulty=summary_by_difficulty,
        summary_by_model_difficulty=summary_by_model_difficulty,
        summary_by_category=summary_by_category,
        failure_summary=failure_summary,
    )

    success("Raw CSV and JSON benchmark datasets exported.")
    success("Aggregate CSV and LaTeX tables exported.")
    success("Markdown analysis report exported.")

    generated_figures = generate_graphs(results, graphs_dir)

    if generated_figures:
        success(f"{generated_figures} academic figures generated in {graphs_dir}")
    else:
        warning("No figures were generated. Check the dataset and plotting dependencies.")

    logging.info("Result export completed for %d benchmark attempts.", len(results))
