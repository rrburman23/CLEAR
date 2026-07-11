"""Tabular export helpers for CLEAR experiment reports."""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any, Iterable


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
    """Write dictionaries to a UTF-8 CSV file.

    An empty file is created when no columns are available.  This behaviour is
    useful for failure summaries when an experiment records no failures.
    """

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
    """Build a Markdown table from rows and ``(field, heading)`` columns."""

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
    """Escape text that has special meaning in LaTeX tables.

    Escaping is performed character by character so replacement strings are
    never processed a second time.
    """

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
    """Write a standalone ``table`` environment without pandas dependency."""

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
        values = [
            _escape_latex(format_value(row.get(field)))
            for field, _ in columns
        ]
        lines.append(" & ".join(values) + r" \\")

    lines.extend(
        [
            r"\hline",
            r"\end{tabular}",
            r"\end{table}",
            "",
        ]
    )

    destination.write_text("\n".join(lines), encoding="utf-8")
