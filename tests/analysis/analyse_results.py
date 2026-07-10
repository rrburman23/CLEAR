"""
CLEAR Dataset Analysis

Reads the aggregated benchmark dataset (tests/analysis/dataset.csv) and
produces every quantitative artefact required for the dissertation:

    analysis_out/
    ├── summary_metrics.csv        one row per model: SR, Pass@1, TTR,
    │                              IE, ARI, FR (+ across-run std where
    │                              multiple run_ids exist)
    ├── summary_metrics.md         the same table as paste-ready Markdown
    ├── category_matrix.csv        success rate per model x category
    ├── failure_reasons.csv        failure taxonomy counts per model
    └── graphs/
        ├── sr_pass1_by_model.png
        ├── ttr_by_model.png
        ├── category_heatmap.png
        └── failure_distribution.png

Usage:
    python tests/analysis/analyze_results.py
    python tests/analysis/analyze_results.py --input path/to/dataset.csv
"""

import argparse
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# =========================================================
# Metric Computation
# =========================================================


def per_model_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes the six dissertation metrics for a single run (or a pooled
    frame). SR/Pass@1/FR use all attempts; TTR/IE/ARI use successful
    repairs only, matching the definitions in the write-up.
    """
    rows = []
    for model, g in df.groupby("model"):
        total = len(g)
        ok = g[g["passed"]]
        successful = len(ok)

        # Pass@1: Repair success where iterations == 1
        pass1 = len(g[(g["passed"] == True) & (g["iterations"] == 1)])

        rows.append(
            {
                "model": model,
                "total": total,
                "SR_pct": 100 * successful / total if total else 0.0,
                "Pass@1_pct": 100 * pass1 / total
                if total
                else 0.0,  # Pass@1 calculation
                "TTR_s": ok["ttr"].mean() if successful else np.nan,
                "IE": (1 / ok["iterations"]).mean() if successful else np.nan,
                "ARI": ok["iterations"].mean() if successful else np.nan,
                "FR_pct": 100 * (total - successful) / total if total else 0.0,
            }
        )
    return pd.DataFrame(rows)


def summarise(df: pd.DataFrame) -> pd.DataFrame:
    """
    If multiple run_ids exist, computes metrics per run then reports
    mean +/- std across runs. With a single run, reports point values.
    """
    runs = sorted(df["run_id"].unique())
    per_run = [per_model_metrics(df[df["run_id"] == r]).assign(run_id=r) for r in runs]
    stacked = pd.concat(per_run, ignore_index=True)

    metric_cols = ["SR_pct", "Pass@1_pct", "TTR_s", "IE", "ARI", "FR_pct"]

    if len(runs) == 1:
        out = stacked.drop(columns=["run_id"]).copy()
        out["n_runs"] = 1
        return out.sort_values("SR_pct", ascending=False).round(3)

    agg = stacked.groupby("model").agg(
        total=("total", "first"),
        **{f"{c}_mean": (c, "mean") for c in metric_cols},
        **{f"{c}_std": (c, "std") for c in metric_cols},
    )
    agg["n_runs"] = len(runs)
    return agg.reset_index().sort_values("SR_pct_mean", ascending=False).round(3)


def category_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Success rate (%) per model x category, pooled across runs."""
    pivot = df.pivot_table(
        index="model", columns="category", values="passed", aggfunc="mean"
    )
    return (100 * pivot).round(1)


def failure_reasons(df: pd.DataFrame) -> pd.DataFrame:
    failed = df[~df["passed"]].copy()
    failed["failure_reason"] = (
        failed["failure_reason"].fillna("unknown").replace("", "unknown")
    )
    return (
        failed.groupby(["model", "failure_reason"])
        .size()
        .reset_index(name="count")
        .sort_values(["model", "count"], ascending=[True, False])
    )


# =========================================================
# Markdown Table Export
# =========================================================


def to_markdown_table(summary: pd.DataFrame) -> str:
    """
    Exports summary metrics to a clean, paste-ready Markdown table.
    Handles both single-run point values and multi-run mean/std formats.
    """
    header = "| Model | N | SR (%) | Pass@1 (%) | TTR (s) | IE | ARI | FR (%) |"
    sep = "|---|---|---|---|---|---|---|---|"
    lines = [header, sep]

    for _, r in summary.iterrows():
        # Check if we are dealing with multi-run summary (mean/std) or single run
        is_multi = "SR_pct_mean" in summary.columns

        if not is_multi:
            # Single run formatting
            lines.append(
                f"| {r['model']} | {int(r['total'])} | {r['SR_pct']:.1f} "
                f"| {r['Pass@1_pct']:.1f} | {r['TTR_s']:.2f} "
                f"| {r['IE']:.3f} | {r['ARI']:.2f} | {r['FR_pct']:.1f} |"
            )
        else:
            # Multi-run mean ± std formatting
            # Helper to create 'mean ± std' string
            def fmt(col):
                m, s = r[f"{col}_mean"], r[f"{col}_std"]
                # If std is 0.0, just show mean to keep the table clean
                if pd.isna(s) or s == 0:
                    return (
                        f"{m:.2f}"
                        if col != "SR_pct" and col != "Pass@1_pct" and col != "FR_pct"
                        else f"{m:.1f}"
                    )
                return f"{m:.1f} ± {s:.1f}" if "pct" in col else f"{m:.2f} ± {s:.2f}"

            lines.append(
                f"| {r['model']} | {int(r['total'])} | {fmt('SR_pct')} "
                f"| {fmt('Pass@1_pct')} | {fmt('TTR_s')} "
                f"| {fmt('IE')} | {fmt('ARI')} | {fmt('FR_pct')} |"
            )

    return "\n".join(lines)


# =========================================================
# Graphs
# =========================================================




def plot_ttr(df: pd.DataFrame, path: str):
    ok = df[df["passed"]]
    models = sorted(ok["model"].unique())
    data = [ok[ok["model"] == m]["ttr"].values for m in models]
    fig, ax = plt.subplots(figsize=(max(8, 1.1 * len(models) + 3), 5))
    ax.boxplot(data, tick_labels=models, showmeans=True)
    ax.set_ylabel("Time to Resolution (s)")
    ax.set_title("TTR Distribution by Model (successful repairs)")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_heatmap(matrix: pd.DataFrame, path: str):
    fig, ax = plt.subplots(
        figsize=(1.1 * len(matrix.columns) + 3, 0.6 * len(matrix.index) + 2)
    )
    image = ax.imshow(matrix.values, cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(range(len(matrix.columns)), matrix.columns, rotation=30, ha="right")
    ax.set_yticks(range(len(matrix.index)), matrix.index)
    for i in range(len(matrix.index)):
        for j in range(len(matrix.columns)):
            v = matrix.values[i][j]
            if v == v:
                ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=8)
    fig.colorbar(image, label="Success Rate (%)")
    ax.set_title("Success Rate by Model and Fault Category")
    plt.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_failures(fr: pd.DataFrame, path: str):
    if fr.empty:
        return
    counts = fr.groupby("failure_reason")["count"].sum().sort_values()
    fig, ax = plt.subplots(figsize=(9, max(3, 0.5 * len(counts) + 1.5)))
    ax.barh(counts.index, counts.values, color="#c0504d")
    ax.set_xlabel("Occurrences (all models)")
    ax.set_title("Failure Taxonomy Distribution")
    plt.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)

def plot_sr_pass1(summary: pd.DataFrame, path: str):
    single = "SR_pct" in summary.columns
    models = summary["model"]
    sr = summary["SR_pct"] if single else summary["SR_pct_mean"]
    p1 = summary["Pass@1_pct"] if single else summary["Pass@1_pct_mean"]
    sr_err = None if single else summary["SR_pct_std"]

    x = np.arange(len(models))
    width = 0.35  # Explicit float, not an array
    fig, ax = plt.subplots(figsize=(max(8, 1.1 * len(models) + 3), 5))

    # Use standard list/array conversion to be safe
    ax.bar(
        x - width / 2,
        sr.values.astype(float), 
        width,
        yerr=sr_err.values.astype(float) if sr_err is not None else None,
        capsize=3,
        label="Success Rate (SR)",
        color="#4c9f70",
    )
    ax.bar(
        x + width / 2, p1.values.astype(float), width, label="Pass@1", color="#4a7fb5"
    )

    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=30, ha="right")
    ax.set_ylabel("Rate (%)")
    ax.set_ylim(0, 105)
    ax.set_title("Success Rate vs Pass@1 by Model")
    ax.legend()
    plt.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
# =========================================================
# Main
# =========================================================


def main():
    parser = argparse.ArgumentParser(description="CLEAR dataset analysis")
    parser.add_argument("--input", default="tests/analysis/dataset.csv")
    parser.add_argument("--output", default="tests/analysis/analysis_out")
    args = parser.parse_args()

    df = pd.read_csv(args.input)

    # Normalise types (CSV booleans arrive as strings)
    if df["passed"].dtype == object:
        df["passed"] = df["passed"].astype(str).str.lower().isin(["true", "1"])
    if "run_id" not in df.columns:
        df["run_id"] = 1
    df["run_id"] = df["run_id"].fillna(1)

    os.makedirs(args.output, exist_ok=True)
    graphs_dir = os.path.join(args.output, "graphs")
    os.makedirs(graphs_dir, exist_ok=True)

    summary = summarise(df)
    matrix = category_matrix(df)
    fr = failure_reasons(df)

    summary.to_csv(os.path.join(args.output, "summary_metrics.csv"), index=False)
    matrix.to_csv(os.path.join(args.output, "category_matrix.csv"))
    fr.to_csv(os.path.join(args.output, "failure_reasons.csv"), index=False)

    md = to_markdown_table(summary)
    with open(
        os.path.join(args.output, "summary_metrics.md"), "w", encoding="utf-8"
    ) as h:
        h.write(md + "\n")

    plot_sr_pass1(summary, os.path.join(graphs_dir, "sr_pass1_by_model.png"))
    plot_ttr(df, os.path.join(graphs_dir, "ttr_by_model.png"))
    plot_heatmap(matrix, os.path.join(graphs_dir, "category_heatmap.png"))
    plot_failures(fr, os.path.join(graphs_dir, "failure_distribution.png"))

    n_runs = df["run_id"].nunique()
    print(
        f"Records: {len(df)}  |  Models: {df['model'].nunique()}  "
        f"|  Categories: {df['category'].nunique()}  |  Runs: {n_runs}"
    )
    print(f"\nOutputs written to: {os.path.abspath(args.output)}\n")
    print(md)


if __name__ == "__main__":
    main()
