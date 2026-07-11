"""
CLEAR Result Export Utilities

Exports one benchmark experiment to:

    run_directory/
    ├── dataset.csv
    ├── dataset.json
    ├── summary_by_model.csv
    ├── summary_by_difficulty.csv
    ├── summary_by_model_difficulty.csv
    ├── failure_summary.csv
    ├── analysis_report.md
    └── graphs/
        ├── fig_01_success_rate_by_model.png
        ├── fig_02_mean_ttr_by_model.png
        ├── fig_03_success_rate_by_difficulty.png
        ├── fig_04_model_difficulty_heatmap.png
        ├── fig_05_ttr_by_difficulty.png
        ├── fig_06_iterations_by_difficulty.png
        ├── fig_07_failures_by_difficulty.png
        └── fig_08_success_rate_by_category.png
"""

from __future__ import annotations

import csv
import json
import logging
import math
import os
from collections import defaultdict
from datetime import datetime
from typing import Any

from src.utils.terminal import success, warning


DIFFICULTY_ORDER = [
    "single_fault",
    "compound_same_category",
    "compound_cross_category",
]

DIFFICULTY_LABELS = {
    "single_fault": "T1: Single-Fault",
    "compound_same_category": ("T2: Homogeneous Compound"),
    "compound_cross_category": ("T3: Heterogeneous Compound"),
}

DATASET_FIELDS = [
    "model",
    "difficulty",
    "difficulty_tier",
    "difficulty_code",
    "difficulty_label",
    "difficulty_definition",
    "category",
    "benchmark",
    "benchmark_id",
    "passed",
    "verified",
    "ttr",
    "wall_time",
    "iterations",
    "failure_reason",
    "return_code",
    "timed_out",
]


# =========================================================
# Data Normalisation
# =========================================================


def normalise_record(
    record: dict[str, Any],
) -> dict[str, Any]:
    """
    Return a record containing every standard dataset field.
    """

    return {field: record.get(field) for field in DATASET_FIELDS}


def safe_mean(
    values: list[float],
) -> float | None:
    """
    Return a mean or None for an empty collection.
    """

    if not values:
        return None

    return sum(values) / len(values)


# =========================================================
# Summary Calculation
# =========================================================


def summarise_records(
    records: list[dict[str, Any]],
    group_fields: list[str],
) -> list[dict[str, Any]]:
    """
    Calculate CLEAR metrics grouped by the supplied fields.

    TTR, IE and ARI use verified successful repairs only.
    SR, Pass@1 and FR use every attempted benchmark.
    """

    groups: dict[
        tuple[Any, ...],
        list[dict[str, Any]],
    ] = defaultdict(list)

    for record in records:
        key = tuple(record.get(field) for field in group_fields)

        groups[key].append(record)

    summaries: list[dict[str, Any]] = []

    for key, group in groups.items():
        total = len(group)

        successful = [record for record in group if record.get("passed") is True]

        failed = total - len(successful)

        first_attempt_successes = sum(
            1 for record in successful if record.get("iterations") == 1
        )

        successful_ttr = [
            float(record["ttr"])
            for record in successful
            if record.get("ttr") is not None
        ]

        successful_wall_time = [
            float(record["wall_time"])
            for record in successful
            if record.get("wall_time") is not None
        ]

        successful_iterations = [
            int(record["iterations"])
            for record in successful
            if (
                isinstance(
                    record.get("iterations"),
                    (int, float),
                )
                and record["iterations"] > 0
            )
        ]

        inverse_iterations = [1 / iterations for iterations in successful_iterations]

        row = {
            field: value
            for field, value in zip(
                group_fields,
                key,
                strict=True,
            )
        }

        row.update(
            {
                "attempts": total,
                "successes": len(successful),
                "failures": failed,
                "success_rate_pct": (100 * len(successful) / total if total else 0.0),
                "pass_at_1_pct": (
                    100 * first_attempt_successes / total if total else 0.0
                ),
                "mean_ttr_s": safe_mean(successful_ttr),
                "mean_wall_time_s": safe_mean(successful_wall_time),
                "iteration_efficiency": (safe_mean(inverse_iterations)),
                "average_repair_iterations": (
                    safe_mean([float(value) for value in successful_iterations])
                ),
                "failure_rate_pct": (100 * failed / total if total else 0.0),
            }
        )

        summaries.append(row)

    return summaries


def build_failure_summary(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Count failures by model, difficulty and reason.
    """

    counts: dict[
        tuple[str, str, str],
        int,
    ] = defaultdict(int)

    for record in records:
        if record.get("passed") is True:
            continue

        model = str(record.get("model") or "unknown")

        difficulty = str(record.get("difficulty") or "unknown")

        reason = str(record.get("failure_reason") or "Unknown repair failure")

        counts[
            (
                model,
                difficulty,
                reason,
            )
        ] += 1

    rows = [
        {
            "model": model,
            "difficulty": difficulty,
            "difficulty_display": (
                DIFFICULTY_LABELS.get(
                    difficulty,
                    difficulty,
                )
            ),
            "failure_reason": reason,
            "count": count,
        }
        for (
            model,
            difficulty,
            reason,
        ), count in counts.items()
    ]

    rows.sort(
        key=lambda row: (
            row["model"],
            DIFFICULTY_ORDER.index(row["difficulty"])
            if row["difficulty"] in DIFFICULTY_ORDER
            else 999,
            -row["count"],
            row["failure_reason"],
        )
    )

    return rows


# =========================================================
# File Writers
# =========================================================


def write_csv(
    path: str,
    rows: list[dict[str, Any]],
    fieldnames: list[str] | None = None,
) -> None:
    """
    Write dictionaries to a UTF-8 CSV file.
    """

    if fieldnames is None:
        fieldnames = list(rows[0]) if rows else []

    with open(
        path,
        "w",
        newline="",
        encoding="utf-8",
    ) as file_handle:
        if not fieldnames:
            return

        writer = csv.DictWriter(
            file_handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )

        writer.writeheader()

        writer.writerows(rows)


def format_number(
    value: Any,
    decimal_places: int = 2,
) -> str:
    """
    Format optional numerical values for Markdown.
    """

    if value is None:
        return "N/A"

    if isinstance(value, float) and math.isnan(value):
        return "N/A"

    try:
        return f"{float(value):.{decimal_places}f}"
    except (TypeError, ValueError):
        return str(value)


def markdown_table(
    rows: list[dict[str, Any]],
    columns: list[tuple[str, str]],
) -> str:
    """
    Construct a Markdown table.
    """

    headings = [heading for _, heading in columns]

    output = [
        "| " + " | ".join(headings) + " |",
        "| " + " | ".join("---" for _ in headings) + " |",
    ]

    for row in rows:
        values = []

        for field, _ in columns:
            value = row.get(field)

            if field.endswith("_pct"):
                value = format_number(
                    value,
                    1,
                )

            elif field in {
                "mean_ttr_s",
                "mean_wall_time_s",
                "average_repair_iterations",
            }:
                value = format_number(
                    value,
                    2,
                )

            elif field == "iteration_efficiency":
                value = format_number(
                    value,
                    3,
                )

            elif value is None:
                value = "N/A"

            values.append(str(value))

        output.append("| " + " | ".join(values) + " |")

    return "\n".join(output)


# =========================================================
# Markdown Report
# =========================================================


def write_analysis_report(
    *,
    run_dir: str,
    records: list[dict[str, Any]],
    by_model: list[dict[str, Any]],
    by_difficulty: list[dict[str, Any]],
    by_model_difficulty: list[dict[str, Any]],
    failure_summary: list[dict[str, Any]],
) -> None:
    """
    Write a human-readable experiment report.
    """

    report_path = os.path.join(
        run_dir,
        "analysis_report.md",
    )

    model_columns = [
        ("model", "Model"),
        ("attempts", "N"),
        ("success_rate_pct", "SR (%)"),
        ("pass_at_1_pct", "Pass@1 (%)"),
        ("mean_ttr_s", "TTR (s)"),
        (
            "iteration_efficiency",
            "IE",
        ),
        (
            "average_repair_iterations",
            "ARI",
        ),
        ("failure_rate_pct", "FR (%)"),
    ]

    difficulty_columns = [
        (
            "difficulty_display",
            "Difficulty",
        ),
        ("attempts", "N"),
        ("success_rate_pct", "SR (%)"),
        ("pass_at_1_pct", "Pass@1 (%)"),
        ("mean_ttr_s", "TTR (s)"),
        (
            "average_repair_iterations",
            "ARI",
        ),
        ("failure_rate_pct", "FR (%)"),
    ]

    model_difficulty_rows = []

    for row in by_model_difficulty:
        converted = dict(row)

        converted["difficulty_display"] = DIFFICULTY_LABELS.get(
            str(row.get("difficulty")),
            str(row.get("difficulty")),
        )

        model_difficulty_rows.append(converted)

    difficulty_rows = []

    for row in by_difficulty:
        converted = dict(row)

        converted["difficulty_display"] = DIFFICULTY_LABELS.get(
            str(row.get("difficulty")),
            str(row.get("difficulty")),
        )

        difficulty_rows.append(converted)

    failure_columns = [
        ("model", "Model"),
        (
            "difficulty_display",
            "Difficulty",
        ),
        (
            "failure_reason",
            "Failure reason",
        ),
        ("count", "Count"),
    ]

    content = f"""# CLEAR Benchmark Experiment Report

Generated: {datetime.now().isoformat()}

## Dataset

- Repair attempts: {len(records)}
- Models: {len({record.get("model") for record in records})}
- Difficulty levels: {len({record.get("difficulty") for record in records})}
- Categories: {len({record.get("category") for record in records})}
- Benchmarks: {len({record.get("benchmark_id") for record in records})}

## Overall Model Performance

{markdown_table(by_model, model_columns)}

## Performance by Difficulty

{markdown_table(difficulty_rows, difficulty_columns)}

## Model × Difficulty Performance

{
        markdown_table(
            model_difficulty_rows,
            [
                ("model", "Model"),
                ("difficulty_display", "Difficulty"),
                ("attempts", "N"),
                ("success_rate_pct", "SR (%)"),
                ("pass_at_1_pct", "Pass@1 (%)"),
                ("mean_ttr_s", "TTR (s)"),
                ("average_repair_iterations", "ARI"),
                ("failure_rate_pct", "FR (%)"),
            ],
        )
    }

## Failure Analysis

{
        markdown_table(
            failure_summary,
            failure_columns,
        )
        if failure_summary
        else "No failures were recorded."
    }

## Difficulty Definitions

| Tier | Folder | Dissertation label | Definition |
|---|---|---|---|
| Tier 1 | `single_fault` | Single-Fault Repair | One intentionally seeded defect |
| Tier 2 | `compound_same_category` | Homogeneous Compound-Fault Repair | Multiple defects from one fault category |
| Tier 3 | `compound_cross_category` | Heterogeneous Compound-Fault Repair | Multiple defects from different categories |
"""

    with open(
        report_path,
        "w",
        encoding="utf-8",
    ) as file_handle:
        file_handle.write(content)


# =========================================================
# Graph Generation
# =========================================================


def generate_graphs(
    records: list[dict[str, Any]],
    run_dir: str,
) -> None:
    """
    Generate academic experiment figures.

    Graph generation is optional. CSV and JSON exports still succeed when
    pandas or matplotlib are unavailable.
    """

    try:
        import matplotlib

        matplotlib.use("Agg")

        import matplotlib.pyplot as plt
        import numpy as np
        import pandas as pd

    except ImportError as exc:
        warning(
            "Graph generation skipped because a data-science "
            f"dependency is unavailable: {exc}"
        )
        return

    if not records:
        warning("Graph generation skipped because the dataset is empty.")
        return

    graph_dir = os.path.join(
        run_dir,
        "graphs",
    )

    os.makedirs(
        graph_dir,
        exist_ok=True,
    )

    frame = pd.DataFrame(records)

    frame["passed"] = frame["passed"].astype(bool)

    frame["difficulty_display"] = (
        frame["difficulty"].map(DIFFICULTY_LABELS).fillna(frame["difficulty"])
    )

    difficulty_display_order = [
        DIFFICULTY_LABELS[difficulty]
        for difficulty in DIFFICULTY_ORDER
        if difficulty in set(frame["difficulty"])
    ]

    # -----------------------------------------------------
    # Figure 1: Success Rate by Model
    # -----------------------------------------------------

    model_success = (
        frame.groupby("model")["passed"].mean().mul(100).sort_values(ascending=False)
    )

    figure, axis = plt.subplots(
        figsize=(
            max(9, len(model_success) * 1.1),
            5,
        )
    )

    model_success.plot(
        kind="bar",
        ax=axis,
    )

    axis.set_title("Verified Repair Success Rate by Model")

    axis.set_xlabel("Model")

    axis.set_ylabel("Success Rate (%)")

    axis.set_ylim(
        0,
        105,
    )

    axis.tick_params(
        axis="x",
        rotation=35,
    )

    figure.tight_layout()

    figure.savefig(
        os.path.join(
            graph_dir,
            "fig_01_success_rate_by_model.png",
        ),
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(figure)

    # -----------------------------------------------------
    # Figure 2: Mean Successful TTR by Model
    # -----------------------------------------------------

    successful = frame[frame["passed"]].copy()

    if not successful.empty:
        model_ttr = successful.groupby("model")["ttr"].mean().sort_values()

        figure, axis = plt.subplots(
            figsize=(
                max(9, len(model_ttr) * 1.1),
                5,
            )
        )

        model_ttr.plot(
            kind="bar",
            ax=axis,
        )

        axis.set_title("Mean Time to Resolution by Model")

        axis.set_xlabel("Model")

        axis.set_ylabel("Mean TTR (seconds)")

        axis.tick_params(
            axis="x",
            rotation=35,
        )

        figure.tight_layout()

        figure.savefig(
            os.path.join(
                graph_dir,
                "fig_02_mean_ttr_by_model.png",
            ),
            dpi=300,
            bbox_inches="tight",
        )

        plt.close(figure)

    # -----------------------------------------------------
    # Figure 3: Success Rate by Difficulty
    # -----------------------------------------------------

    difficulty_success = (
        frame.groupby("difficulty_display")["passed"]
        .mean()
        .mul(100)
        .reindex(difficulty_display_order)
        .dropna()
    )

    figure, axis = plt.subplots(figsize=(9, 5))

    difficulty_success.plot(
        kind="bar",
        ax=axis,
    )

    axis.set_title("Verified Repair Success Rate by Difficulty")

    axis.set_xlabel("Difficulty")

    axis.set_ylabel("Success Rate (%)")

    axis.set_ylim(
        0,
        105,
    )

    axis.tick_params(
        axis="x",
        rotation=20,
    )

    figure.tight_layout()

    figure.savefig(
        os.path.join(
            graph_dir,
            "fig_03_success_rate_by_difficulty.png",
        ),
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(figure)

    # -----------------------------------------------------
    # Figure 4: Model × Difficulty Heatmap
    # -----------------------------------------------------

    heatmap = frame.pivot_table(
        index="model",
        columns="difficulty_display",
        values="passed",
        aggfunc="mean",
    ).mul(100)

    available_columns = [
        column for column in difficulty_display_order if column in heatmap.columns
    ]

    heatmap = heatmap.reindex(columns=available_columns)

    figure, axis = plt.subplots(
        figsize=(
            max(8, len(heatmap.columns) * 2.6),
            max(5, len(heatmap.index) * 0.65),
        )
    )

    image = axis.imshow(
        heatmap.values,
        aspect="auto",
        vmin=0,
        vmax=100,
    )

    axis.set_xticks(range(len(heatmap.columns)))

    axis.set_xticklabels(
        heatmap.columns,
        rotation=25,
        ha="right",
    )

    axis.set_yticks(range(len(heatmap.index)))

    axis.set_yticklabels(heatmap.index)

    for row_index in range(len(heatmap.index)):
        for column_index in range(len(heatmap.columns)):
            value = heatmap.iloc[
                row_index,
                column_index,
            ]

            if pd.notna(value):
                axis.text(
                    column_index,
                    row_index,
                    f"{value:.1f}%",
                    ha="center",
                    va="center",
                )

    figure.colorbar(
        image,
        ax=axis,
        label="Success Rate (%)",
    )

    axis.set_title("Model × Difficulty Success Rate")

    figure.tight_layout()

    figure.savefig(
        os.path.join(
            graph_dir,
            "fig_04_model_difficulty_heatmap.png",
        ),
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(figure)

    # -----------------------------------------------------
    # Figure 5: Successful TTR by Difficulty
    # -----------------------------------------------------

    if not successful.empty:
        successful["difficulty_display"] = (
            successful["difficulty"]
            .map(DIFFICULTY_LABELS)
            .fillna(successful["difficulty"])
        )

        ttr_data = [
            successful.loc[
                successful["difficulty_display"] == difficulty,
                "ttr",
            ]
            .dropna()
            .to_numpy()
            for difficulty in difficulty_display_order
        ]

        non_empty = [
            (
                difficulty,
                values,
            )
            for difficulty, values in zip(
                difficulty_display_order,
                ttr_data,
                strict=True,
            )
            if len(values) > 0
        ]

        if non_empty:
            labels = [item[0] for item in non_empty]

            values = [item[1] for item in non_empty]

            figure, axis = plt.subplots(figsize=(10, 5))

            axis.boxplot(
                values,
                tick_labels=labels,
                showmeans=True,
            )

            axis.set_title("Time to Resolution Distribution by Difficulty")

            axis.set_xlabel("Difficulty")

            axis.set_ylabel("TTR (seconds)")

            axis.tick_params(
                axis="x",
                rotation=20,
            )

            figure.tight_layout()

            figure.savefig(
                os.path.join(
                    graph_dir,
                    "fig_05_ttr_by_difficulty.png",
                ),
                dpi=300,
                bbox_inches="tight",
            )

            plt.close(figure)

    # -----------------------------------------------------
    # Figure 6: Iterations by Difficulty
    # -----------------------------------------------------

    successful_iterations = successful[successful["iterations"] > 0].copy()

    if not successful_iterations.empty:
        iteration_means = (
            successful_iterations.groupby("difficulty_display")["iterations"]
            .mean()
            .reindex(difficulty_display_order)
            .dropna()
        )

        figure, axis = plt.subplots(figsize=(9, 5))

        iteration_means.plot(
            kind="bar",
            ax=axis,
        )

        axis.set_title("Mean Successful Repair Iterations by Difficulty")

        axis.set_xlabel("Difficulty")

        axis.set_ylabel("Mean Repair Iterations")

        axis.tick_params(
            axis="x",
            rotation=20,
        )

        figure.tight_layout()

        figure.savefig(
            os.path.join(
                graph_dir,
                "fig_06_iterations_by_difficulty.png",
            ),
            dpi=300,
            bbox_inches="tight",
        )

        plt.close(figure)

    # -----------------------------------------------------
    # Figure 7: Failure Reasons by Difficulty
    # -----------------------------------------------------

    failed = frame[~frame["passed"]].copy()

    if not failed.empty:
        failed["failure_reason"] = failed["failure_reason"].fillna(
            "Unknown repair failure"
        )

        failure_pivot = (
            failed.groupby(
                [
                    "difficulty_display",
                    "failure_reason",
                ]
            )
            .size()
            .unstack(fill_value=0)
            .reindex(difficulty_display_order)
            .fillna(0)
        )

        figure, axis = plt.subplots(
            figsize=(
                11,
                6,
            )
        )

        failure_pivot.plot(
            kind="bar",
            stacked=True,
            ax=axis,
        )

        axis.set_title("Failure Reasons by Difficulty")

        axis.set_xlabel("Difficulty")

        axis.set_ylabel("Failure Count")

        axis.tick_params(
            axis="x",
            rotation=20,
        )

        axis.legend(
            title="Failure Reason",
            bbox_to_anchor=(
                1.02,
                1,
            ),
            loc="upper left",
        )

        figure.tight_layout()

        figure.savefig(
            os.path.join(
                graph_dir,
                "fig_07_failures_by_difficulty.png",
            ),
            dpi=300,
            bbox_inches="tight",
        )

        plt.close(figure)

    # -----------------------------------------------------
    # Figure 8: Success Rate by Category
    # -----------------------------------------------------

    category_success = (
        frame.groupby("category")["passed"].mean().mul(100).sort_values(ascending=False)
    )

    figure, axis = plt.subplots(
        figsize=(
            max(10, len(category_success) * 0.85),
            5,
        )
    )

    category_success.plot(
        kind="bar",
        ax=axis,
    )

    axis.set_title("Verified Repair Success Rate by Fault Category")

    axis.set_xlabel("Fault Category")

    axis.set_ylabel("Success Rate (%)")

    axis.set_ylim(
        0,
        105,
    )

    axis.tick_params(
        axis="x",
        rotation=35,
    )

    figure.tight_layout()

    figure.savefig(
        os.path.join(
            graph_dir,
            "fig_08_success_rate_by_category.png",
        ),
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(figure)

    success(f"8 academic figures generated in {graph_dir}")


# =========================================================
# Public Export Function
# =========================================================


def export_results(
    raw_execution_data: list[dict[str, Any]],
    run_dir: str,
) -> None:
    """
    Export raw records, summaries, report and graphs.
    """

    os.makedirs(
        run_dir,
        exist_ok=True,
    )

    records = [normalise_record(record) for record in raw_execution_data]

    by_model = summarise_records(
        records,
        ["model"],
    )

    by_difficulty = summarise_records(
        records,
        ["difficulty"],
    )

    by_model_difficulty = summarise_records(
        records,
        [
            "model",
            "difficulty",
        ],
    )

    failure_summary = build_failure_summary(records)

    write_csv(
        os.path.join(
            run_dir,
            "dataset.csv",
        ),
        records,
        DATASET_FIELDS,
    )

    write_csv(
        os.path.join(
            run_dir,
            "summary_by_model.csv",
        ),
        by_model,
    )

    write_csv(
        os.path.join(
            run_dir,
            "summary_by_difficulty.csv",
        ),
        by_difficulty,
    )

    write_csv(
        os.path.join(
            run_dir,
            "summary_by_model_difficulty.csv",
        ),
        by_model_difficulty,
    )

    write_csv(
        os.path.join(
            run_dir,
            "failure_summary.csv",
        ),
        failure_summary,
    )

    json_payload = {
        "generated_at": (datetime.now().isoformat()),
        "schema_version": "2.0",
        "difficulty_definitions": {
            "single_fault": {
                "tier": 1,
                "label": ("Single-Fault Repair"),
                "definition": ("One intentionally seeded defect"),
            },
            "compound_same_category": {
                "tier": 2,
                "label": ("Homogeneous Compound-Fault Repair"),
                "definition": ("Multiple defects from one fault category"),
            },
            "compound_cross_category": {
                "tier": 3,
                "label": ("Heterogeneous Compound-Fault Repair"),
                "definition": ("Multiple defects from different categories"),
            },
        },
        "records": records,
        "summary_by_model": by_model,
        "summary_by_difficulty": (by_difficulty),
        "summary_by_model_difficulty": (by_model_difficulty),
        "failure_summary": failure_summary,
    }

    with open(
        os.path.join(
            run_dir,
            "dataset.json",
        ),
        "w",
        encoding="utf-8",
    ) as file_handle:
        json.dump(
            json_payload,
            file_handle,
            indent=2,
            ensure_ascii=False,
        )

    write_analysis_report(
        run_dir=run_dir,
        records=records,
        by_model=by_model,
        by_difficulty=by_difficulty,
        by_model_difficulty=(by_model_difficulty),
        failure_summary=failure_summary,
    )

    success("CSV datasets and summaries exported.")

    success("JSON advanced dataset exported.")

    success("Markdown analysis report exported.")

    logging.info("Data-science libraries detected. Generating academic figures...")

    generate_graphs(
        records,
        run_dir,
    )
