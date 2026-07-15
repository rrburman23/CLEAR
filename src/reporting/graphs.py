"""Academic figure generation for CLEAR benchmark experiments.

The module intentionally uses matplotlib directly rather than seaborn so the
reporting pipeline has a small and predictable plotting dependency surface.
Every function creates one independent figure and closes it after export.
All plots use publication-ready styling, specific figure scales, explicit labels,
and error margins optimized for scientific review.
"""

from __future__ import annotations

import logging
import math
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.benchmarking.difficulty import ordered_difficulties
from src.benchmarking.models import BenchmarkResult

if TYPE_CHECKING:
    import matplotlib.pyplot as plt
    import pandas as pd
    import numpy as np


# Centralized academic color palette for consistent model class presentation
CLASS_COLORS = {
    "Code-Specialized": "#1f77b4",  # Classic Academic Blue
    "General-Purpose": "#ff7f0e",  # Safety Orange
    "Intrinsic Reasoning": "#2ca02c",  # Research Green
    "Resource-Efficient": "#9467bd",  # Technical Purple
    "Other": "#7f7f7f",  # Neutral Gray
}

# Strict structural mapping of directory strings to formal dissertation labels
TIER_LABELS = {
    "single_fault": "Tier 1: Single-Fault",
    "compound_same_category": "Tier 2: Homogeneous Compound",
    "compound_cross_category": "Tier 3: Heterogeneous Compound",
}

TIER_ORDER = [
    "Tier 1: Single-Fault",
    "Tier 2: Homogeneous Compound",
    "Tier 3: Heterogeneous Compound",
]


def _load_plotting_libraries() -> tuple[Any, Any] | None:
    """Load optional plotting dependencies using a headless backend."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import pandas as pd

        # Configure publication-grade styling properties globally
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["axes.edgecolor"] = "#333333"
        plt.rcParams["axes.linewidth"] = 0.8
        plt.rcParams["xtick.color"] = "#333333"
        plt.rcParams["ytick.color"] = "#333333"
    except ImportError as exc:
        logging.warning("Graph generation skipped: %s", exc)
        return None
    return plt, pd


def _difficulty_order(frame: Any) -> list[str]:
    """Return difficulty labels present in the dataset in canonical tier order."""
    present = set(frame["difficulty"].dropna().astype(str))
    return [
        difficulty.label
        for difficulty in ordered_difficulties()
        if difficulty.name in present
    ]


def _prepare_frame(results: list[BenchmarkResult], pd: Any) -> Any:
    """Convert typed results into a plotting DataFrame with safe dtypes."""
    frame = pd.DataFrame(result.to_dict() for result in results)

    if frame.empty:
        return frame

    # Required defaults including the structural complexity tier fields
    for column, default in {
        "passed": False,
        "iterations": 0,
        "ttr": math.nan,
        "tier": "single_fault",
        "difficulty": "",
        "difficulty_label": "",
        "model": "unknown",
        "category": "unknown",
        "failure_reason": None,
    }.items():
        if column not in frame.columns:
            frame[column] = default

    frame["passed"] = frame["passed"].astype(bool)
    frame["iterations"] = (
        pd.to_numeric(frame["iterations"], errors="coerce").fillna(0).astype(int)
    )
    frame["ttr"] = pd.to_numeric(frame["ttr"], errors="coerce")
    frame["difficulty_display"] = (
        frame["difficulty_label"].fillna(frame["difficulty"]).astype(str)
    )

    # Map raw folder paths to clean scientific dissertation nomenclature
    frame["tier_display"] = (
        frame["tier"].map(TIER_LABELS).fillna(frame["tier"]).astype(str)
    )

    return frame


def _model_parameter_billions(model_name: str) -> float | None:
    """Infer parameter count in billions from model naming conventions."""
    name = model_name.lower()

    if "phi3:mini" in name:
        return 3.8
    if "ornith:9b" in name:
        return 9.0

    match = re.search(r":(\d+(?:\.\d+)?)b", name)
    if match:
        return float(match.group(1))

    return None


def _wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for binomial proportion."""
    if n == 0:
        return 0.0, 0.0

    p = successes / n
    denom = 1 + (z * z) / n
    center = (p + (z * z) / (2 * n)) / denom
    margin = (z / denom) * math.sqrt((p * (1 - p) / n) + (z * z) / (4 * n * n))
    return max(0.0, center - margin), min(1.0, center + margin)


def plot_success_rate_by_model(frame: Any, destination: Path, plt: Any) -> None:
    values = (
        frame.groupby("model")["passed"].mean().mul(100).sort_values(ascending=False)
    )

    figure, axis = plt.subplots(figsize=(max(9, len(values) * 1.1), 5))
    values.plot(kind="bar", ax=axis, color="#1f77b4", edgecolor="#115588", zorder=3)
    axis.set_title(
        "Verified Repair Success Rate (SR) by Model",
        fontsize=12,
        fontweight="bold",
        pad=15,
    )
    axis.set_xlabel("Language Model Baseline", fontsize=10, labelpad=10)
    axis.set_ylabel("Success Rate (%)", fontsize=10, labelpad=10)
    axis.set_ylim(0, 105)
    axis.grid(True, axis="y", linestyle="--", alpha=0.5, zorder=0)
    axis.tick_params(axis="x", rotation=30, labelsize=9)
    figure.tight_layout()
    figure.savefig(destination, dpi=300, bbox_inches="tight")
    plt.close(figure)


def plot_mean_ttr_by_model(frame: Any, destination: Path, plt: Any) -> bool:
    successful = frame[frame["passed"]]
    if successful.empty:
        return False

    values = successful.groupby("model")["ttr"].mean().sort_values()

    figure, axis = plt.subplots(figsize=(max(9, len(values) * 1.1), 5))
    values.plot(kind="bar", ax=axis, color="#d62728", edgecolor="#991111", zorder=3)
    axis.set_title(
        "Mean Time to Resolution (TTR) among Successful Repairs",
        fontsize=12,
        fontweight="bold",
        pad=15,
    )
    axis.set_xlabel("Language Model Baseline", fontsize=10, labelpad=10)
    axis.set_ylabel("Mean TTR (seconds)", fontsize=10, labelpad=10)
    axis.grid(True, axis="y", linestyle="--", alpha=0.5, zorder=0)
    axis.tick_params(axis="x", rotation=30, labelsize=9)
    figure.tight_layout()
    figure.savefig(destination, dpi=300, bbox_inches="tight")
    plt.close(figure)
    return True


def plot_success_rate_by_difficulty(frame: Any, destination: Path, plt: Any) -> None:
    order = _difficulty_order(frame)
    values = (
        frame.groupby("difficulty_display")["passed"]
        .mean()
        .mul(100)
        .reindex(order)
        .dropna()
    )

    figure, axis = plt.subplots(figsize=(9, 5))
    values.plot(kind="bar", ax=axis, color="#7f7f7f", edgecolor="#444444", zorder=3)
    axis.set_title(
        "Verified Repair Success Rate by Leaf Difficulty Attribute",
        fontsize=12,
        fontweight="bold",
        pad=15,
    )
    axis.set_xlabel("Seeded Domain Distinctions", fontsize=10, labelpad=10)
    axis.set_ylabel("Success Rate (%)", fontsize=10, labelpad=10)
    axis.set_ylim(0, 105)
    axis.grid(True, axis="y", linestyle="--", alpha=0.5, zorder=0)
    axis.tick_params(axis="x", rotation=25, labelsize=9)
    figure.tight_layout()
    figure.savefig(destination, dpi=300, bbox_inches="tight")
    plt.close(figure)


def plot_model_difficulty_heatmap(
    frame: Any, destination: Path, plt: Any, pd: Any
) -> None:
    order = _difficulty_order(frame)
    matrix = (
        frame.pivot_table(
            index="model", columns="difficulty_display", values="passed", aggfunc="mean"
        )
        .mul(100)
        .reindex(columns=order)
    )

    figure, axis = plt.subplots(
        figsize=(max(8, len(matrix.columns) * 2.8), max(5, len(matrix.index) * 0.65))
    )
    image = axis.imshow(matrix.values, aspect="auto", vmin=0, vmax=100, cmap="Blues")

    axis.set_xticks(range(len(matrix.columns)))
    axis.set_xticklabels(matrix.columns, rotation=25, ha="right", fontsize=9)
    axis.set_yticks(range(len(matrix.index)))
    axis.set_yticklabels(matrix.index, fontsize=9)

    for row_index in range(len(matrix.index)):
        for column_index in range(len(matrix.columns)):
            value = matrix.iloc[row_index, column_index]
            if pd.notna(value):
                color = "white" if value > 60 else "black"
                axis.text(
                    column_index,
                    row_index,
                    f"{value:.1f}%",
                    ha="center",
                    va="center",
                    color=color,
                    fontsize=9,
                    fontweight="bold",
                )

    figure.colorbar(image, ax=axis, label="Success Rate (%)")
    axis.set_title(
        "Structural Matrix: Model × Fine-Grained Difficulty SR",
        fontsize=12,
        fontweight="bold",
        pad=15,
    )
    figure.tight_layout()
    figure.savefig(destination, dpi=300, bbox_inches="tight")
    plt.close(figure)


def plot_success_rate_by_category(frame: Any, destination: Path, plt: Any) -> None:
    values = (
        frame.groupby("category")["passed"].mean().mul(100).sort_values(ascending=False)
    )

    figure, axis = plt.subplots(figsize=(max(10, len(values) * 0.85), 5))
    values.plot(kind="bar", ax=axis, color="#2ca02c", edgecolor="#116611", zorder=3)
    axis.set_title(
        "Verified Repair Success Rate by Fault Category",
        fontsize=12,
        fontweight="bold",
        pad=15,
    )
    axis.set_xlabel("Taxonomy Categories", fontsize=10, labelpad=10)
    axis.set_ylabel("Success Rate (%)", fontsize=10, labelpad=10)
    axis.set_ylim(0, 105)
    axis.grid(True, axis="y", linestyle="--", alpha=0.5, zorder=0)
    axis.tick_params(axis="x", rotation=35, labelsize=9)
    figure.tight_layout()
    figure.savefig(destination, dpi=300, bbox_inches="tight")
    plt.close(figure)


def plot_failures_by_model(frame: Any, destination: Path, plt: Any) -> bool:
    failed = frame[~frame["passed"]].copy()
    if failed.empty:
        return False

    failed["failure_reason"] = failed["failure_reason"].fillna("Unknown repair failure")
    model_order = frame.groupby("model")["passed"].mean().sort_values().index

    matrix = (
        failed.groupby(["model", "failure_reason"])
        .size()
        .unstack(fill_value=0)
        .reindex(model_order)
        .fillna(0)
    )

    figure, axis = plt.subplots(figsize=(12, 6))
    matrix.plot(kind="bar", stacked=True, ax=axis, cmap="tab20", zorder=3)
    axis.set_title(
        "Absolute Failures Composition Analysis across Baselines",
        fontsize=12,
        fontweight="bold",
        pad=15,
    )
    axis.set_xlabel("Language Model Baseline", fontsize=10, labelpad=10)
    axis.set_ylabel("Failure Frequency (Counts)", fontsize=10, labelpad=10)
    axis.grid(True, axis="y", linestyle="--", alpha=0.5, zorder=0)
    axis.tick_params(axis="x", rotation=30, labelsize=9)
    axis.legend(
        title="Structural Root Cause",
        bbox_to_anchor=(1.02, 1),
        loc="upper left",
        fontsize=9,
    )
    figure.tight_layout()
    figure.savefig(destination, dpi=300, bbox_inches="tight")
    plt.close(figure)
    return True


def plot_cumulative_success_by_iteration(
    frame: Any, destination: Path, plt: Any
) -> bool:
    if frame.empty:
        return False

    model_order = (
        frame.groupby("model")["passed"].mean().sort_values(ascending=False).index
    )
    max_iters_value = frame["iterations"].max()
    max_iters = int(max_iters_value) if max_iters_value and max_iters_value > 0 else 15
    iterations_range = list(range(1, max_iters + 1))

    figure, axis = plt.subplots(figsize=(10, 6))

    for model in model_order:
        model_data = frame[frame["model"] == model]
        total_tasks = len(model_data)
        if total_tasks == 0:
            continue

        cumulative_rates = []
        for i in iterations_range:
            resolved_at_i = len(
                model_data[model_data["passed"] & (model_data["iterations"] <= i)]
            )
            cumulative_rates.append((resolved_at_i / total_tasks) * 100)

        axis.plot(
            iterations_range,
            cumulative_rates,
            marker="o",
            markersize=4,
            label=model,
            linewidth=1.8,
        )

    axis.set_title(
        "Cumulative Verified Repair Success by Iteration)",
        fontsize=12,
        fontweight="bold",
        pad=15,
    )
    axis.set_xlabel("Repair Attempt Limit (k)", fontsize=10, labelpad=10)
    axis.set_ylabel("Cumulative Success Rate (%)", fontsize=10, labelpad=10)
    axis.set_xlim(1, max_iters)
    axis.set_ylim(0, 105)
    axis.grid(True, linestyle="--", alpha=0.5)
    axis.legend(
        title="Model Evaluated", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9
    )

    figure.tight_layout()
    figure.savefig(destination, dpi=300, bbox_inches="tight")
    plt.close(figure)
    return True


def plot_pass_at_1_by_model(frame: Any, destination: Path, plt: Any) -> bool:
    values = (
        frame.assign(pass_at_1=(frame["passed"]) & (frame["iterations"] == 1))
        .groupby("model")["pass_at_1"]
        .mean()
        .mul(100)
        .sort_values(ascending=False)
    )

    figure, axis = plt.subplots(figsize=(max(9, len(values) * 1.1), 5))
    values.plot(kind="bar", ax=axis, color="#bcbd22", edgecolor="#888811", zorder=3)
    axis.set_title(
        "Zero-Shot Adaptive Intuition: Pass@1 Success Ratio",
        fontsize=12,
        fontweight="bold",
        pad=15,
    )
    axis.set_xlabel("Language Model Baseline", fontsize=10, labelpad=10)
    axis.set_ylabel("Pass@1 (%)", fontsize=10, labelpad=10)
    axis.set_ylim(0, 105)
    axis.grid(True, axis="y", linestyle="--", alpha=0.5, zorder=0)
    axis.tick_params(axis="x", rotation=30, labelsize=9)
    figure.tight_layout()
    figure.savefig(destination, dpi=300, bbox_inches="tight")
    plt.close(figure)
    return True


def plot_iteration_gain_by_model(frame: Any, destination: Path, plt: Any) -> None:
    """Plot SR - Pass@1 by model to show where iteration provides gains."""
    grouped = frame.groupby("model")
    sr = grouped["passed"].mean().mul(100)
    p1 = grouped.apply(
        lambda df: ((df["passed"]) & (df["iterations"] == 1)).mean() * 100
    )
    gain = (sr - p1).sort_values(ascending=False)

    figure, axis = plt.subplots(figsize=(max(9, len(gain) * 1.1), 5))
    gain.plot(kind="bar", ax=axis, color="#17becf", edgecolor="#118899", zorder=3)
    axis.set_title(
        "Closed-Loop Feedback Yield: Iteration Delta (SR − Pass@1)",
        fontsize=12,
        fontweight="bold",
        pad=15,
    )
    axis.set_xlabel("Language Model Baseline", fontsize=10, labelpad=10)
    axis.set_ylabel(
        "Differential Capacity Boost (percentage points)", fontsize=10, labelpad=10
    )
    axis.tick_params(axis="x", rotation=30, labelsize=9)
    axis.grid(True, axis="y", linestyle="--", alpha=0.5, zorder=0)
    axis.axhline(0, color="#333333", linewidth=1)
    figure.tight_layout()
    figure.savefig(destination, dpi=300, bbox_inches="tight")
    plt.close(figure)


def plot_failure_share_by_model(frame: Any, destination: Path, plt: Any) -> bool:
    """Normalized (%) failure composition by model."""
    failed = frame[~frame["passed"]].copy()
    if failed.empty:
        return False

    failed["failure_reason"] = failed["failure_reason"].fillna("Unknown repair failure")
    counts = failed.groupby(["model", "failure_reason"]).size().unstack(fill_value=0)
    percentages = counts.div(counts.sum(axis=1), axis=0).mul(100)

    model_order = frame.groupby("model")["passed"].mean().sort_values().index
    percentages = percentages.reindex(model_order).fillna(0)

    figure, axis = plt.subplots(figsize=(12, 6))
    percentages.plot(kind="bar", stacked=True, ax=axis, cmap="tab20", zorder=3)
    axis.set_title(
        "Normalized Failure Taxonomy Spectrum Composition (%)",
        fontsize=12,
        fontweight="bold",
        pad=15,
    )
    axis.set_xlabel("Language Model Baseline", fontsize=10, labelpad=10)
    axis.set_ylabel("Proportional Share of Errors (%)", fontsize=10, labelpad=10)
    axis.set_ylim(0, 100)
    axis.tick_params(axis="x", rotation=30, labelsize=9)
    axis.grid(True, axis="y", linestyle="--", alpha=0.3, zorder=0)
    axis.legend(
        title="Structural Cause", bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9
    )
    figure.tight_layout()
    figure.savefig(destination, dpi=300, bbox_inches="tight")
    plt.close(figure)
    return True


def plot_success_rate_ci_by_model(
    frame: Any,
    destination: Path,
    plt: Any,
) -> None:
    """
    Plot success rate by model with Wilson 95% confidence intervals.

    Error distances are clamped to zero because floating-point rounding can
    otherwise produce extremely small negative values at boundaries such as
    a 100% observed success rate. Matplotlib rejects negative ``yerr`` values.
    """

    grouped = frame.groupby("model")

    models: list[str] = []
    rates: list[float] = []
    lower_errors: list[float] = []
    upper_errors: list[float] = []

    for model, group in grouped:
        sample_size = len(group)
        successes = int(group["passed"].sum())

        success_rate = (
            (successes / sample_size) * 100.0
            if sample_size
            else 0.0
        )

        lower_bound, upper_bound = _wilson_interval(
            successes=successes,
            n=sample_size,
            z=1.96,
        )

        lower_bound_percent = lower_bound * 100.0
        upper_bound_percent = upper_bound * 100.0

        # Floating-point arithmetic can produce values such as
        # -1.42e-14 when the observed rate is exactly 100%.
        lower_error = max(
            0.0,
            success_rate - lower_bound_percent,
        )

        upper_error = max(
            0.0,
            upper_bound_percent - success_rate,
        )

        models.append(str(model))
        rates.append(success_rate)
        lower_errors.append(lower_error)
        upper_errors.append(upper_error)

    order = sorted(
        range(len(models)),
        key=lambda index: rates[index],
        reverse=True,
    )

    models = [models[index] for index in order]
    rates = [rates[index] for index in order]
    lower_errors = [lower_errors[index] for index in order]
    upper_errors = [upper_errors[index] for index in order]

    figure, axis = plt.subplots(
        figsize=(
            max(
                9,
                len(models) * 1.1,
            ),
            5,
        )
    )

    axis.bar(
        models,
        rates,
        color="#9467bd",
        edgecolor="#553388",
        alpha=0.8,
        zorder=3,
    )

    axis.errorbar(
        models,
        rates,
        yerr=[
            lower_errors,
            upper_errors,
        ],
        fmt="none",
        ecolor="#111111",
        capsize=4,
        elinewidth=1.2,
        zorder=4,
    )

    axis.set_title(
        "Verified Repair Success Rate with Wilson 95% Confidence Intervals",
        fontsize=12,
        fontweight="bold",
        pad=15,
    )

    axis.set_xlabel(
        "Language Model",
        fontsize=10,
        labelpad=10,
    )

    axis.set_ylabel(
        "Success Rate (%)",
        fontsize=10,
        labelpad=10,
    )

    axis.set_ylim(
        0,
        105,
    )

    axis.grid(
        True,
        axis="y",
        linestyle="--",
        alpha=0.5,
        zorder=0,
    )

    axis.tick_params(
        axis="x",
        rotation=30,
        labelsize=9,
    )

    figure.tight_layout()

    figure.savefig(
        destination,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(figure)


def plot_success_rate_vs_parameter_count(
    frame: Any, destination: Path, plt: Any
) -> bool:
    """Scatter: parameter count (B) vs success rate."""
    grouped = frame.groupby("model")["passed"].mean().mul(100)

    points = []
    for model, success in grouped.items():
        params = _model_parameter_billions(str(model))
        if params is not None:
            points.append((str(model), params, float(success)))

    if not points:
        return False

    figure, axis = plt.subplots(figsize=(8.5, 6))
    xs = [p[1] for p in points]
    ys = [p[2] for p in points]
    axis.scatter(
        xs, ys, s=70, color="#d62728", edgecolor="#333333", alpha=0.8, zorder=3
    )

    for model, x, y in points:
        axis.annotate(
            f" {model.split(':')[0]}", (x, y), fontsize=8, fontweight="medium"
        )

    axis.set_title(
        "Scaling Laws Analysis: Success Rate vs Parameter Dimension",
        fontsize=12,
        fontweight="bold",
        pad=15,
    )
    axis.set_xlabel("Parameters Scaling Floor (Billions)", fontsize=10, labelpad=10)
    axis.set_ylabel("System Success Rate (%)", fontsize=10, labelpad=10)
    axis.set_ylim(-5, 105)
    axis.grid(True, linestyle="--", alpha=0.4, zorder=0)

    figure.tight_layout()
    figure.savefig(destination, dpi=300, bbox_inches="tight")
    plt.close(figure)
    return True


def plot_success_rate_by_model_class(frame: Any, destination: Path, plt: Any) -> None:
    """Aggregate success by manually defined model paradigm classes."""
    class_map = {
        "qwen2.5-coder:7b": "Code-Specialized",
        "granite-code:8b": "Code-Specialized",
        "codegemma:7b": "Code-Specialized",
        "codellama:7b": "Code-Specialized",
        "llama3.1:8b": "General-Purpose",
        "gemma2:9b": "General-Purpose",
        "mistral-nemo:12b": "General-Purpose",
        "deepseek-r1:8b": "Intrinsic Reasoning",
        "ornith:9b": "Intrinsic Reasoning",  # Added Ornith 1.0 architecture
        "qwen2.5-coder:3b": "Resource-Efficient",
        "phi3:mini": "Resource-Efficient",
    }

    copy = frame.copy()
    copy["model_class"] = copy["model"].map(class_map).fillna("Other")
    values = (
        copy.groupby("model_class")["passed"]
        .mean()
        .mul(100)
        .sort_values(ascending=False)
    )

    figure, axis = plt.subplots(figsize=(8, 5))
    colors = [CLASS_COLORS.get(c, CLASS_COLORS["Other"]) for c in values.index]

    values.plot(kind="bar", ax=axis, color=colors, edgecolor="#333333", zorder=3)
    axis.set_title(
        "Macro Paradigm Evaluation: Aggregate Performance by Architecture Class",
        fontsize=12,
        fontweight="bold",
        pad=15,
    )
    axis.set_xlabel("Architectural Class Paradigm", fontsize=10, labelpad=10)
    axis.set_ylabel("Success Rate (%)", fontsize=10, labelpad=10)
    axis.set_ylim(0, 115)
    axis.grid(True, axis="y", linestyle="--", alpha=0.5, zorder=0)
    axis.tick_params(axis="x", rotation=0, labelsize=10)

    for i, value in enumerate(values):
        axis.text(
            i, value + 2, f"{value:.1f}%", ha="center", fontweight="bold", fontsize=10
        )

    figure.tight_layout()
    figure.savefig(destination, dpi=300, bbox_inches="tight")
    plt.close(figure)


# =========================================================
# NEW: Taxonomy Tier Graphs for Dissertation
# =========================================================


def plot_success_rate_by_tier(frame: Any, destination: Path, plt: Any) -> None:
    """Isolates the absolute success rates across the three descriptive complexity tiers."""
    values = (
        frame.groupby("tier_display")["passed"]
        .mean()
        .mul(100)
        .reindex(TIER_ORDER)
        .fillna(0)
    )

    figure, axis = plt.subplots(figsize=(8, 5))
    values.plot(
        kind="bar",
        ax=axis,
        color=["#2196F3", "#4CAF50", "#FF9800"],
        edgecolor="#222222",
        zorder=3,
    )
    axis.set_title(
        "Taxonomy Capability Analysis: Success Rate by Structural Complexity Tier",
        fontsize=12,
        fontweight="bold",
        pad=15,
    )
    axis.set_xlabel(
        "Taxonomy Difficulty Classification Tiers", fontsize=10, labelpad=10
    )
    axis.set_ylabel("Aggregate Success Rate (%)", fontsize=10, labelpad=10)
    axis.set_ylim(0, 115)
    axis.grid(True, axis="y", linestyle="--", alpha=0.5, zorder=0)
    axis.tick_params(axis="x", rotation=0, labelsize=9)

    for i, value in enumerate(values):
        axis.text(
            i, value + 2, f"{value:.1f}%", ha="center", fontweight="bold", fontsize=10
        )

    figure.tight_layout()
    figure.savefig(destination, dpi=300, bbox_inches="tight")
    plt.close(figure)


def plot_model_tier_decay_matrix(frame: Any, destination: Path, plt: Any) -> None:
    """Generates a grouped clustering chart isolating capability degradation as complexity tiers escalate."""
    model_order = (
        frame.groupby("model")["passed"].mean().sort_values(ascending=False).index
    )

    # Generate grouped pivots
    pivot = (
        frame.pivot_table(
            index="model", columns="tier_display", values="passed", aggfunc="mean"
        )
        .mul(100)
        .reindex(index=model_order, columns=TIER_ORDER)
        .fillna(0)
    )

    figure, axis = plt.subplots(figsize=(12, 6))
    pivot.plot(
        kind="bar",
        ax=axis,
        width=0.8,
        color=["#64B5F6", "#81C784", "#FFB74D"],
        edgecolor="#333333",
        zorder=3,
    )

    axis.set_title(
        "The Complexity Cascade: Capability Decay Across Difficulty Tiers",
        fontsize=12,
        fontweight="bold",
        pad=15,
    )
    axis.set_xlabel("Language Model Baseline", fontsize=10, labelpad=10)
    axis.set_ylabel("Success Rate (%)", fontsize=10, labelpad=10)
    axis.set_ylim(0, 105)
    axis.grid(True, axis="y", linestyle="--", alpha=0.5, zorder=0)
    axis.tick_params(axis="x", rotation=30, labelsize=9)
    axis.legend(title="Complexity Classification", loc="upper right", fontsize=9)

    figure.tight_layout()
    figure.savefig(destination, dpi=300, bbox_inches="tight")
    plt.close(figure)


# =========================================================
# Main Graph Pipeline Handler
# =========================================================


def generate_graphs(
    results: list[BenchmarkResult], output_directory: str | Path
) -> int:
    """Generate dissertation-ready figures and return number written."""
    libraries = _load_plotting_libraries()
    if libraries is None or not results:
        return 0

    plt, pd = libraries
    destination = Path(output_directory)
    destination.mkdir(parents=True, exist_ok=True)

    frame = _prepare_frame(results, pd)
    if frame.empty:
        return 0

    generated = 0

    # T1: Core model tracking figures
    plot_success_rate_by_model(
        frame, destination / "fig_01_success_rate_by_model.png", plt
    )
    generated += 1
    if plot_mean_ttr_by_model(frame, destination / "fig_02_mean_ttr_by_model.png", plt):
        generated += 1
    if plot_pass_at_1_by_model(
        frame, destination / "fig_03_pass_at_1_by_model.png", plt
    ):
        generated += 1
    plot_iteration_gain_by_model(
        frame, destination / "fig_04_iteration_gain_by_model.png", plt
    )
    generated += 1
    plot_success_rate_ci_by_model(
        frame, destination / "fig_05_success_rate_ci_by_model.png", plt
    )
    generated += 1

    # T2: Structural Complexity and Taxonomy Tier Figures (NEW)
    plot_success_rate_by_tier(
        frame, destination / "fig_06_success_rate_by_tier.png", plt
    )
    generated += 1
    plot_model_tier_decay_matrix(
        frame, destination / "fig_07_model_tier_decay_matrix.png", plt
    )
    generated += 1

    # T3: Fine-grained leaves and category heatmaps
    plot_success_rate_by_difficulty(
        frame, destination / "fig_08_success_rate_by_difficulty.png", plt
    )
    generated += 1
    plot_model_difficulty_heatmap(
        frame, destination / "fig_09_model_difficulty_heatmap.png", plt, pd
    )
    generated += 1
    plot_success_rate_by_category(
        frame, destination / "fig_10_success_rate_by_category.png", plt
    )
    generated += 1

    # T4: Execution trajectory timelines and trace taxonomies
    if plot_cumulative_success_by_iteration(
        frame, destination / "fig_11_cumulative_success_by_iteration.png", plt
    ):
        generated += 1
    if plot_failures_by_model(
        frame, destination / "fig_12_failures_by_model_counts.png", plt
    ):
        generated += 1
    if plot_failure_share_by_model(
        frame, destination / "fig_13_failure_share_by_model_pct.png", plt
    ):
        generated += 1

    # T5: Parameter dimension and architectural scaling matrices
    plot_success_rate_by_model_class(
        frame, destination / "fig_14_success_rate_by_model_class.png", plt
    )
    generated += 1
    if plot_success_rate_vs_parameter_count(
        frame, destination / "fig_15_success_vs_parameter_count.png", plt
    ):
        generated += 1

    return generated
