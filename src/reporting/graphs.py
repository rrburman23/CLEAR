"""Academic figure generation for CLEAR benchmark experiments.

The module intentionally uses matplotlib directly rather than seaborn so the
reporting pipeline has a small and predictable plotting dependency surface.
Every function creates one independent figure and closes it after export.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.benchmarking.difficulty import ordered_difficulties
from src.benchmarking.models import BenchmarkResult

if TYPE_CHECKING:
    import matplotlib.pyplot as plt
    import pandas as pd


def _load_plotting_libraries() -> tuple[Any, Any] | None:
    """Load optional plotting dependencies using a headless backend."""

    try:
        import matplotlib

        matplotlib.use("Agg")

        import matplotlib.pyplot as plt
        import pandas as pd

    except ImportError as exc:
        logging.warning("Graph generation skipped: %s", exc)
        return None

    return plt, pd


def _difficulty_order(frame: Any) -> list[str]:
    """Return difficulty labels present in the dataset in tier order."""

    present = set(frame["difficulty"].dropna().astype(str))

    return [
        difficulty.label
        for difficulty in ordered_difficulties()
        if difficulty.name in present
    ]


def _prepare_frame(results: list[BenchmarkResult], pd: Any) -> Any:
    """Convert typed results into a plotting DataFrame."""

    frame = pd.DataFrame(result.to_dict() for result in results)
    frame["passed"] = frame["passed"].astype(bool)
    frame["difficulty_display"] = frame["difficulty_label"]
    return frame


def plot_success_rate_by_model(frame: Any, destination: Path, plt: Any) -> None:
    """Plot verified repair success rate for every model."""

    values = (
        frame.groupby("model")["passed"]
        .mean()
        .mul(100)
        .sort_values(ascending=False)
    )

    figure, axis = plt.subplots(figsize=(max(9, len(values) * 1.1), 5))
    values.plot(kind="bar", ax=axis)
    axis.set_title("Verified Repair Success Rate by Model")
    axis.set_xlabel("Model")
    axis.set_ylabel("Success Rate (%)")
    axis.set_ylim(0, 105)
    axis.tick_params(axis="x", rotation=35)
    figure.tight_layout()
    figure.savefig(destination, dpi=300, bbox_inches="tight")
    plt.close(figure)


def plot_mean_ttr_by_model(frame: Any, destination: Path, plt: Any) -> bool:
    """Plot mean successful time to resolution for every model."""

    successful = frame[frame["passed"]]

    if successful.empty:
        return False

    values = successful.groupby("model")["ttr"].mean().sort_values()

    figure, axis = plt.subplots(figsize=(max(9, len(values) * 1.1), 5))
    values.plot(kind="bar", ax=axis)
    axis.set_title("Mean Time to Resolution by Model")
    axis.set_xlabel("Model")
    axis.set_ylabel("Mean TTR (seconds)")
    axis.tick_params(axis="x", rotation=35)
    figure.tight_layout()
    figure.savefig(destination, dpi=300, bbox_inches="tight")
    plt.close(figure)
    return True


def plot_success_rate_by_difficulty(
    frame: Any,
    destination: Path,
    plt: Any,
) -> None:
    """Plot repair success rate for the three dissertation tiers."""

    order = _difficulty_order(frame)
    values = (
        frame.groupby("difficulty_display")["passed"]
        .mean()
        .mul(100)
        .reindex(order)
        .dropna()
    )

    figure, axis = plt.subplots(figsize=(9, 5))
    values.plot(kind="bar", ax=axis)
    axis.set_title("Verified Repair Success Rate by Difficulty")
    axis.set_xlabel("Difficulty")
    axis.set_ylabel("Success Rate (%)")
    axis.set_ylim(0, 105)
    axis.tick_params(axis="x", rotation=20)
    figure.tight_layout()
    figure.savefig(destination, dpi=300, bbox_inches="tight")
    plt.close(figure)


def plot_model_difficulty_heatmap(
    frame: Any,
    destination: Path,
    plt: Any,
    pd: Any,
) -> None:
    """Plot a percentage-labelled model-by-difficulty success heatmap."""

    order = _difficulty_order(frame)
    matrix = (
        frame.pivot_table(
            index="model",
            columns="difficulty_display",
            values="passed",
            aggfunc="mean",
        )
        .mul(100)
        .reindex(columns=order)
    )

    figure, axis = plt.subplots(
        figsize=(
            max(8, len(matrix.columns) * 2.8),
            max(5, len(matrix.index) * 0.65),
        )
    )

    image = axis.imshow(matrix.values, aspect="auto", vmin=0, vmax=100)
    axis.set_xticks(range(len(matrix.columns)))
    axis.set_xticklabels(matrix.columns, rotation=25, ha="right")
    axis.set_yticks(range(len(matrix.index)))
    axis.set_yticklabels(matrix.index)

    for row_index in range(len(matrix.index)):
        for column_index in range(len(matrix.columns)):
            value = matrix.iloc[row_index, column_index]

            if pd.notna(value):
                axis.text(
                    column_index,
                    row_index,
                    f"{value:.1f}%",
                    ha="center",
                    va="center",
                )

    figure.colorbar(image, ax=axis, label="Success Rate (%)")
    axis.set_title("Model × Difficulty Success Rate")
    figure.tight_layout()
    figure.savefig(destination, dpi=300, bbox_inches="tight")
    plt.close(figure)


def plot_ttr_by_difficulty(frame: Any, destination: Path, plt: Any) -> bool:
    """Plot successful TTR distributions for each difficulty tier."""

    successful = frame[frame["passed"]]

    if successful.empty:
        return False

    labels = _difficulty_order(successful)
    datasets = [
        successful.loc[
            successful["difficulty_display"] == label,
            "ttr",
        ]
        .dropna()
        .to_numpy()
        for label in labels
    ]

    populated = [
        (label, values)
        for label, values in zip(labels, datasets, strict=True)
        if len(values) > 0
    ]

    if not populated:
        return False

    figure, axis = plt.subplots(figsize=(10, 5))
    axis.boxplot(
        [values for _, values in populated],
        tick_labels=[label for label, _ in populated],
        showmeans=True,
    )
    axis.set_title("Time to Resolution Distribution by Difficulty")
    axis.set_xlabel("Difficulty")
    axis.set_ylabel("TTR (seconds)")
    axis.tick_params(axis="x", rotation=20)
    figure.tight_layout()
    figure.savefig(destination, dpi=300, bbox_inches="tight")
    plt.close(figure)
    return True


def plot_iterations_by_difficulty(
    frame: Any,
    destination: Path,
    plt: Any,
) -> bool:
    """Plot successful repair-attempt distributions by difficulty."""

    successful = frame[(frame["passed"]) & (frame["iterations"] > 0)]

    if successful.empty:
        return False

    labels = _difficulty_order(successful)
    datasets = [
        successful.loc[
            successful["difficulty_display"] == label,
            "iterations",
        ]
        .dropna()
        .to_numpy()
        for label in labels
    ]

    populated = [
        (label, values)
        for label, values in zip(labels, datasets, strict=True)
        if len(values) > 0
    ]

    if not populated:
        return False

    figure, axis = plt.subplots(figsize=(10, 5))
    axis.boxplot(
        [values for _, values in populated],
        tick_labels=[label for label, _ in populated],
        showmeans=True,
    )
    axis.set_title("Repair Iteration Distribution by Difficulty")
    axis.set_xlabel("Difficulty")
    axis.set_ylabel("Repair Iterations")
    axis.tick_params(axis="x", rotation=20)
    figure.tight_layout()
    figure.savefig(destination, dpi=300, bbox_inches="tight")
    plt.close(figure)
    return True


def plot_failures_by_difficulty(
    frame: Any,
    destination: Path,
    plt: Any,
) -> bool:
    """Plot a stacked failure-reason count for every difficulty tier."""

    failed = frame[~frame["passed"]].copy()

    if failed.empty:
        return False

    failed["failure_reason"] = failed["failure_reason"].fillna(
        "Unknown repair failure"
    )
    order = _difficulty_order(failed)

    matrix = (
        failed.groupby(["difficulty_display", "failure_reason"])
        .size()
        .unstack(fill_value=0)
        .reindex(order)
        .fillna(0)
    )

    figure, axis = plt.subplots(figsize=(11, 6))
    matrix.plot(kind="bar", stacked=True, ax=axis)
    axis.set_title("Failure Reasons by Difficulty")
    axis.set_xlabel("Difficulty")
    axis.set_ylabel("Failure Count")
    axis.tick_params(axis="x", rotation=20)
    axis.legend(
        title="Failure Reason",
        bbox_to_anchor=(1.02, 1),
        loc="upper left",
    )
    figure.tight_layout()
    figure.savefig(destination, dpi=300, bbox_inches="tight")
    plt.close(figure)
    return True


def plot_success_rate_by_category(
    frame: Any,
    destination: Path,
    plt: Any,
) -> None:
    """Plot verified repair success rate by fault category."""

    values = (
        frame.groupby("category")["passed"]
        .mean()
        .mul(100)
        .sort_values(ascending=False)
    )

    figure, axis = plt.subplots(figsize=(max(10, len(values) * 0.85), 5))
    values.plot(kind="bar", ax=axis)
    axis.set_title("Verified Repair Success Rate by Fault Category")
    axis.set_xlabel("Fault Category")
    axis.set_ylabel("Success Rate (%)")
    axis.set_ylim(0, 105)
    axis.tick_params(axis="x", rotation=35)
    figure.tight_layout()
    figure.savefig(destination, dpi=300, bbox_inches="tight")
    plt.close(figure)


def generate_graphs(
    results: list[BenchmarkResult],
    output_directory: str | Path,
) -> int:
    """Generate all available figures and return the number written."""

    libraries = _load_plotting_libraries()

    if libraries is None or not results:
        return 0

    plt, pd = libraries
    destination = Path(output_directory)
    destination.mkdir(parents=True, exist_ok=True)
    frame = _prepare_frame(results, pd)
    generated = 0

    plot_success_rate_by_model(
        frame,
        destination / "fig_01_success_rate_by_model.png",
        plt,
    )
    generated += 1

    if plot_mean_ttr_by_model(
        frame,
        destination / "fig_02_mean_ttr_by_model.png",
        plt,
    ):
        generated += 1

    plot_success_rate_by_difficulty(
        frame,
        destination / "fig_03_success_rate_by_difficulty.png",
        plt,
    )
    generated += 1

    plot_model_difficulty_heatmap(
        frame,
        destination / "fig_04_model_difficulty_heatmap.png",
        plt,
        pd,
    )
    generated += 1

    if plot_ttr_by_difficulty(
        frame,
        destination / "fig_05_ttr_by_difficulty.png",
        plt,
    ):
        generated += 1

    if plot_iterations_by_difficulty(
        frame,
        destination / "fig_06_iterations_by_difficulty.png",
        plt,
    ):
        generated += 1

    if plot_failures_by_difficulty(
        frame,
        destination / "fig_07_failures_by_difficulty.png",
        plt,
    ):
        generated += 1

    plot_success_rate_by_category(
        frame,
        destination / "fig_08_success_rate_by_category.png",
        plt,
    )
    generated += 1

    return generated
