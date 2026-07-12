"""Tabular export helpers for CLEAR experiment reports."""

from __future__ import annotations

import csv
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

from src.benchmarking.models import BenchmarkResult


METRIC_COLUMNS = [
    "attempts",
    "successes",
    "failures",
    "success_rate_pct",
    "pass_at_1_pct",
    "mean_ttr_s",
    "mean_wall_time_s",
    "iteration_efficiency",
    "average_repair_iterations",
    "failure_rate_pct",
]


def write_csv(
    path: str | Path,
    rows: list[dict[str, Any]],
    fieldnames: list[str] | None = None,
) -> None:
    """Write dictionaries to a UTF-8 CSV file."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    resolved_fields = fieldnames or (list(rows[0]) if rows else [])

    with destination.open("w", newline="", encoding="utf-8") as handle:
        if not resolved_fields:
            return

        writer = csv.DictWriter(
            handle,
            fieldnames=resolved_fields,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def format_value(value: Any, decimal_places: int = 2) -> str:
    """Format optional values for human-readable reports."""
    if value is None:
        return "N/A"

    if isinstance(value, float) and math.isnan(value):
        return "N/A"

    if isinstance(value, bool):
        return "True" if value else "False"

    if isinstance(value, float):
        return f"{value:.{decimal_places}f}"

    return str(value)


def markdown_table(
    rows: Iterable[dict[str, Any]],
    columns: list[tuple[str, str]],
) -> str:
    """Build a Markdown table from rows and (field, heading) columns."""
    materialised = list(rows)
    headings = [heading for _, heading in columns]

    output = [
        "| " + " | ".join(headings) + " |",
        "| " + " | ".join("---" for _ in headings) + " |",
    ]

    for row in materialised:
        values: list[str] = []
        for field, _ in columns:
            value = row.get(field)

            if field.endswith("_pct"):
                values.append(format_value(value, 1))
            elif field in {
                "mean_ttr_s",
                "mean_wall_time_s",
                "average_repair_iterations",
            }:
                values.append(format_value(value, 2))
            elif field == "iteration_efficiency":
                values.append(format_value(value, 3))
            else:
                values.append(format_value(value))

        output.append("| " + " | ".join(values) + " |")

    return "\n".join(output)


def _escape_latex(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(character, character) for character in value)


def write_latex_table(
    path: str | Path,
    rows: list[dict[str, Any]],
    columns: list[tuple[str, str]],
    caption: str,
    label: str,
) -> None:
    """Write a standalone table environment without pandas dependency."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    column_specification = "l" + "r" * max(0, len(columns) - 1)
    header = " & ".join(_escape_latex(heading) for _, heading in columns)

    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        rf"\caption{{{_escape_latex(caption)}}}",
        rf"\label{{{_escape_latex(label)}}}",
        rf"\begin{{tabular}}{{{column_specification}}}",
        r"\hline",
        header + r" \\",
        r"\hline",
    ]

    for row in rows:
        values = [_escape_latex(format_value(row.get(field))) for field, _ in columns]
        lines.append(" & ".join(values) + r"\\")

    lines.extend(
        [
            r"\hline",
            r"\end{tabular}",
            r"\end{table}",
            "",
        ]
    )

    destination.write_text("\n".join(lines), encoding="utf-8")


# =========================
# Aggregation helpers
# =========================


def _to_rows(results: list[BenchmarkResult]) -> list[dict[str, Any]]:
    return [result.to_dict() for result in results]


def _safe_mean(values: list[float]) -> float | None:
    return mean(values) if values else None


def _metric_row(
    rows: list[dict[str, Any]],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    attempts = len(rows)
    successes = sum(1 for row in rows if bool(row.get("passed")))
    failures = attempts - successes

    pass_at_1_successes = sum(
        1
        for row in rows
        if bool(row.get("passed")) and int(row.get("iterations", 0) or 0) == 1
    )

    successful_rows = [row for row in rows if bool(row.get("passed"))]

    successful_ttr = [
        float(row["ttr"]) for row in successful_rows if row.get("ttr") is not None
    ]
    successful_iters = [
        int(row["iterations"])
        for row in successful_rows
        if row.get("iterations") is not None and int(row["iterations"]) > 0
    ]
    wall_times = [
        float(row["wall_time"]) for row in rows if row.get("wall_time") is not None
    ]

    if successful_iters:
        iteration_efficiency = sum(1.0 / k for k in successful_iters) / len(
            successful_iters
        )
        average_repair_iterations = sum(successful_iters) / len(successful_iters)
    else:
        iteration_efficiency = None
        average_repair_iterations = None

    payload: dict[str, Any] = {
        "attempts": attempts,
        "successes": successes,
        "failures": failures,
        "success_rate_pct": (successes / attempts * 100.0) if attempts else 0.0,
        "pass_at_1_pct": (pass_at_1_successes / attempts * 100.0) if attempts else 0.0,
        "mean_ttr_s": _safe_mean(successful_ttr),
        "mean_wall_time_s": _safe_mean(wall_times),
        "iteration_efficiency": iteration_efficiency,
        "average_repair_iterations": average_repair_iterations,
        "failure_rate_pct": (failures / attempts * 100.0) if attempts else 0.0,
    }

    if extra:
        payload.update(extra)

    return payload


def _most_common_failure(rows: list[dict[str, Any]]) -> str:
    reasons = [
        str(row.get("failure_reason") or "Unknown repair failure")
        for row in rows
        if not bool(row.get("passed"))
    ]
    if not reasons:
        return "N/A"
    return Counter(reasons).most_common(1)[0][0]


# =========================
# Public summary builders
# =========================


def build_model_summary(results: list[BenchmarkResult]) -> list[dict[str, Any]]:
    rows = _to_rows(results)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("model", "unknown"))].append(row)

    output = [
        _metric_row(group_rows, {"model": model})
        for model, group_rows in grouped.items()
    ]
    output.sort(key=lambda row: row["success_rate_pct"], reverse=True)
    return output


def build_model_difficulty_summary(
    results: list[BenchmarkResult],
) -> list[dict[str, Any]]:
    rows = _to_rows(results)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        key = (
            str(row.get("model", "unknown")),
            str(row.get("difficulty_code") or row.get("difficulty") or "unknown"),
        )
        grouped[key].append(row)

    output: list[dict[str, Any]] = []
    for (model, difficulty), group_rows in grouped.items():
        output.append(
            _metric_row(group_rows, {"model": model, "difficulty": difficulty})
        )

    output.sort(key=lambda row: (row["model"], row["difficulty"]))
    return output


def build_model_category_summary(
    results: list[BenchmarkResult],
) -> list[dict[str, Any]]:
    rows = _to_rows(results)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        key = (
            str(row.get("model", "unknown")),
            str(row.get("category", "unknown")),
        )
        grouped[key].append(row)

    output: list[dict[str, Any]] = []
    for (model, category), group_rows in grouped.items():
        output.append(
            _metric_row(
                group_rows,
                {
                    "model": model,
                    "category": category,
                    "top_failure_reason": _most_common_failure(group_rows),
                },
            )
        )

    output.sort(key=lambda row: (row["model"], row["category"]))
    return output


def build_hardest_benchmarks(
    results: list[BenchmarkResult],
    top_n: int = 20,
) -> list[dict[str, Any]]:
    rows = _to_rows(results)
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        key = (
            str(row.get("difficulty_code") or row.get("difficulty") or "unknown"),
            str(row.get("category", "unknown")),
            str(row.get("benchmark", "unknown")),
        )
        grouped[key].append(row)

    output: list[dict[str, Any]] = []
    for (difficulty, category, benchmark), group_rows in grouped.items():
        metric = _metric_row(
            group_rows,
            {
                "difficulty": difficulty,
                "category": category,
                "benchmark": benchmark,
                "most_common_failure_reason": _most_common_failure(group_rows),
            },
        )
        output.append(metric)

    output.sort(
        key=lambda row: (
            row["success_rate_pct"],  # hardest first
            -row["attempts"],  # more evidence first
            row["benchmark"],
        )
    )
    return output[:top_n]


def build_failure_summary(results: list[BenchmarkResult]) -> list[dict[str, Any]]:
    rows = _to_rows(results)
    failed = [row for row in rows if not bool(row.get("passed"))]

    if not failed:
        return []

    counts = Counter(
        str(row.get("failure_reason") or "Unknown repair failure") for row in failed
    )
    total = len(failed)

    output = [
        {
            "failure_reason": reason,
            "count": count,
            "share_of_failures_pct": (count / total) * 100.0,
        }
        for reason, count in counts.most_common()
    ]
    return output


def build_failures_by_model(results: list[BenchmarkResult]) -> list[dict[str, Any]]:
    rows = _to_rows(results)
    failed = [row for row in rows if not bool(row.get("passed"))]
    if not failed:
        return []

    grouped: dict[str, list[str]] = defaultdict(list)
    for row in failed:
        model = str(row.get("model", "unknown"))
        reason = str(row.get("failure_reason") or "Unknown repair failure")
        grouped[model].append(reason)

    output: list[dict[str, Any]] = []
    for model, reasons in grouped.items():
        total = len(reasons)
        counts = Counter(reasons)
        for reason, count in counts.most_common():
            output.append(
                {
                    "model": model,
                    "failure_reason": reason,
                    "count": count,
                    "share_of_model_failures_pct": (count / total) * 100.0,
                }
            )

    output.sort(key=lambda row: (row["model"], -row["count"], row["failure_reason"]))
    return output


def build_pass_at_k_summary(
    results: list[BenchmarkResult],
    ks: Iterable[int] = (1, 2, 3, 5),
) -> list[dict[str, Any]]:
    rows = _to_rows(results)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("model", "unknown"))].append(row)

    k_values = sorted({int(k) for k in ks if int(k) > 0})
    output: list[dict[str, Any]] = []

    for model, model_rows in grouped.items():
        attempts = len(model_rows)
        payload: dict[str, Any] = {"model": model, "attempts": attempts}

        for k in k_values:
            resolved = sum(
                1
                for row in model_rows
                if bool(row.get("passed")) and int(row.get("iterations", 0) or 0) <= k
            )
            payload[f"pass_at_{k}_pct"] = (
                (resolved / attempts * 100.0) if attempts else 0.0
            )

        output.append(payload)

    output.sort(key=lambda row: row.get("pass_at_1_pct", 0.0), reverse=True)
    return output


def build_efficiency_leaderboard(
    results: list[BenchmarkResult],
) -> list[dict[str, Any]]:
    rows = build_model_summary(results)
    # Keep concise leaderboard columns
    output = [
        {
            "model": row["model"],
            "attempts": row["attempts"],
            "success_rate_pct": row["success_rate_pct"],
            "pass_at_1_pct": row["pass_at_1_pct"],
            "mean_ttr_s": row["mean_ttr_s"],
            "average_repair_iterations": row["average_repair_iterations"],
            "iteration_efficiency": row["iteration_efficiency"],
            "failure_rate_pct": row["failure_rate_pct"],
        }
        for row in rows
    ]
    return output
