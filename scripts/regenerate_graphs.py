"""Regenerate CLEAR figures from an existing exported benchmark dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.reporting.graphs import generate_graphs


class ExportedBenchmarkResult:
    """
    Compatibility wrapper for an exported benchmark result.

    The graph-generation pipeline only requires each result object to expose
    a ``to_dict`` method.
    """

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def to_dict(self) -> dict[str, Any]:
        return dict(self._data)


def _extract_result_rows(payload: Any) -> list[dict[str, Any]]:
    """
    Extract individual benchmark rows from common CLEAR JSON structures.
    """

    if isinstance(payload, list):
        rows = payload

    elif isinstance(payload, dict):
        rows = None

        # ADDED "records" to support the dataset schema v4.0
        for key in (
            "results",
            "benchmark_results",
            "raw_results",
            "attempts",
            "data",
            "records",
        ):
            candidate = payload.get(key)

            if isinstance(candidate, list):
                rows = candidate
                break

        if rows is None:
            raise ValueError(
                "The JSON object does not contain an individual-results list. "
                "Expected one of: results, benchmark_results, raw_results, "
                "attempts, data, or records."
            )

    else:
        raise ValueError(
            "The result dataset must contain either a JSON list or JSON object."
        )

    valid_rows = [row for row in rows if isinstance(row, dict)]

    if not valid_rows:
        raise ValueError("No benchmark result records were found in the JSON file.")

    return valid_rows


def _looks_like_raw_results(rows: list[dict[str, Any]]) -> bool:
    """
    Determine whether rows represent individual benchmark executions.
    """

    required_fields = {
        "model",
        "passed",
        "iterations",
    }

    return all(required_fields.issubset(row) for row in rows[: min(10, len(rows))])


def _load_json_results(json_path: Path) -> list[dict[str, Any]]:
    """Load and validate one exported JSON dataset."""

    with json_path.open(
        "r",
        encoding="utf-8",
    ) as file_handle:
        payload = json.load(file_handle)

    rows = _extract_result_rows(payload)

    if not _looks_like_raw_results(rows):
        raise ValueError(
            f"{json_path} does not appear to contain individual benchmark "
            "results. It may be an aggregate metrics file."
        )

    return rows


def _find_results_json(run_directory: Path) -> Path:
    """
    Locate the raw benchmark-results JSON inside an experiment directory.
    """

    preferred_names = (
        "dataset.json",  # Added dataset.json to preferred names
        "benchmark_results.json",
        "raw_results.json",
        "results.json",
        "benchmark_attempts.json",
    )

    for filename in preferred_names:
        candidate = run_directory / filename

        if candidate.is_file():
            try:
                rows = _load_json_results(candidate)
            except (ValueError, json.JSONDecodeError):
                continue

            if rows:
                return candidate

    for candidate in sorted(run_directory.rglob("*.json")):
        try:
            rows = _load_json_results(candidate)
        except (
            OSError,
            ValueError,
            json.JSONDecodeError,
        ):
            continue

        if rows:
            return candidate

    raise FileNotFoundError(
        "Could not locate a JSON file containing individual benchmark "
        f"results under: {run_directory}"
    )


def _normalise_boolean(value: Any) -> bool:
    """Convert exported boolean representations safely."""

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() in {
            "true",
            "1",
            "yes",
            "passed",
            "success",
        }

    return bool(value)


def _normalise_row(row: dict[str, Any]) -> dict[str, Any]:
    """
    Normalise fields required by the plotting pipeline.
    """

    normalised = dict(row)

    normalised["passed"] = _normalise_boolean(
        normalised.get(
            "passed",
            False,
        )
    )

    try:
        normalised["iterations"] = int(
            normalised.get(
                "iterations",
                0,
            )
        )
    except (
        TypeError,
        ValueError,
    ):
        normalised["iterations"] = 0

    try:
        normalised["ttr"] = float(
            normalised.get(
                "ttr",
                0.0,
            )
        )
    except (
        TypeError,
        ValueError,
    ):
        normalised["ttr"] = 0.0

    # graphs.py uses ``tier`` for the structural benchmark folder name.
    if not normalised.get("tier"):
        normalised["tier"] = normalised.get(
            "difficulty",
            "single_fault",
        )

    normalised.setdefault(
        "difficulty",
        "single_fault",
    )

    normalised.setdefault(
        "difficulty_label",
        normalised["difficulty"],
    )

    normalised.setdefault(
        "category",
        "unknown",
    )

    normalised.setdefault(
        "failure_reason",
        None,
    )

    return normalised


def create_parser() -> argparse.ArgumentParser:
    """Create the graph-regeneration command-line parser."""

    parser = argparse.ArgumentParser(
        description=(
            "Regenerate CLEAR benchmark figures from an existing exported "
            "JSON dataset without rerunning model evaluation."
        )
    )

    parser.add_argument(
        "run_directory",
        type=Path,
        help="Existing CLEAR experiment output directory.",
    )

    parser.add_argument(
        "--results-json",
        type=Path,
        default=None,
        help=(
            "Optional explicit path to the individual benchmark-results JSON. "
            "When omitted, the script searches the run directory."
        ),
    )

    parser.add_argument(
        "--output-directory",
        type=Path,
        default=None,
        help=("Optional figure output directory. Default: <run-directory>/graphs."),
    )

    return parser


def main() -> int:
    """Load existing results and regenerate all figures."""

    args = create_parser().parse_args()

    run_directory = args.run_directory.resolve()

    if not run_directory.is_dir():
        raise FileNotFoundError(f"Experiment directory was not found: {run_directory}")

    results_json = (
        args.results_json.resolve()
        if args.results_json is not None
        else _find_results_json(run_directory)
    )

    output_directory = (
        args.output_directory.resolve()
        if args.output_directory is not None
        else run_directory / "graphs"
    )

    raw_rows = _load_json_results(results_json)

    results = [ExportedBenchmarkResult(_normalise_row(row)) for row in raw_rows]

    print(f"Results file: {results_json}")
    print(f"Result records: {len(results)}")
    print(f"Figure directory: {output_directory}")

    generated_count = generate_graphs(
        results=results,
        output_directory=output_directory,
    )

    print(f"Generated figures: {generated_count}")

    if generated_count == 0:
        raise RuntimeError(
            "No figures were generated. Check that matplotlib and pandas "
            "are installed and that the result dataset is non-empty."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
