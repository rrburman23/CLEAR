"""
CLEAR Telemetry Exporter
Handles the serialization of benchmark execution data into machine-readable
flat files (CSV, JSON) for downstream academic analysis.

Generates advanced statistical visualizations (Heatmaps, CDFs, Stacked Bars)
to empirically evaluate SLM cognitive boundaries.
"""

import csv
import json
import os
from typing import List, Dict, Any

from src.utils.terminal import success, warning, info


def export_results(raw_data: List[Dict[str, Any]], run_dir: str) -> None:
    """
    Exports raw execution telemetry to CSV and JSON formats inside the run directory.
    Calculates advanced academic metrics (Pass@1, Category SR) for the JSON payload.
    """
    if not raw_data:
        warning("No raw data collected to export.")
        return

    csv_path = os.path.join(run_dir, "dataset.csv")
    json_path = os.path.join(run_dir, "dataset.json")

    # =========================================================
    # Calculate Advanced Metrics for JSON payload
    # =========================================================
    advanced_metrics = {"aggregate_stats": {}, "raw_execution_data": raw_data}

    # Group data by model
    models = {row["model"] for row in raw_data}

    for model in models:
        model_runs = [r for r in raw_data if r["model"] == model]
        total_runs = len(model_runs)
        success_runs = [r for r in model_runs if r["passed"]]

        # Calculate Pass@1 (First-iteration success)
        pass_at_1 = len([r for r in success_runs if r["iterations"] == 1])

        # Category Breakdown
        categories = {r["category"] for r in model_runs}
        cat_stats = {}
        for cat in categories:
            cat_runs = [r for r in model_runs if r["category"] == cat]
            cat_success = len([r for r in cat_runs if r["passed"]])
            cat_stats[cat] = (cat_success / len(cat_runs)) * 100 if cat_runs else 0

        advanced_metrics["aggregate_stats"][model] = {
            "success_rate_total": (len(success_runs) / total_runs) * 100
            if total_runs
            else 0,
            "pass_at_1_rate": (pass_at_1 / total_runs) * 100 if total_runs else 0,
            "category_success_rates": cat_stats,
        }

    # =========================================================
    # Export to Disk
    # =========================================================
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(advanced_metrics, f, indent=4)
        success("JSON advanced dataset exported to run directory.")
    except Exception as e:
        warning(f"Failed to export JSON: {e}")

    headers = list(raw_data[0].keys())
    try:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(raw_data)
        success("CSV raw dataset exported to run directory.")

        # Create a dedicated graphs subfolder and generate plots
        graphs_dir = os.path.join(run_dir, "graphs")
        os.makedirs(graphs_dir, exist_ok=True)
        _generate_visualizations(csv_path, graphs_dir)

    except Exception as e:
        warning(f"Failed to export CSV: {e}")


def _generate_visualizations(csv_path: str, graphs_dir: str) -> None:
    """
    Generates academic figures for the dissertation Evaluation chapter.
    Requires pandas, matplotlib, and seaborn.
    """
    try:
        import pandas as pd
        import matplotlib.pyplot as plt
        import seaborn as sns

        info("Data science libraries detected. Generating academic figures...")
        df = pd.read_csv(csv_path)
        df["passed"] = df["passed"].astype(bool)

        # Set academic styling
        sns.set_theme(style="whitegrid", palette="muted")

        # =========================================================
        # Figure 1: Success Rate by Architecture (Bar Chart)
        # =========================================================
        plt.figure(figsize=(10, 6))
        sr_data = (
            df.groupby("model")["passed"].mean().sort_values(ascending=False) * 100
        )
        sns.barplot(
            x=sr_data.values,
            y=sr_data.index,
            hue=sr_data.index,
            legend=False,
            palette="viridis",
        )
        plt.title(
            "Autonomous Repair Success Rate (%) by Architecture", fontsize=14, pad=15
        )
        plt.xlabel("Success Rate (%)", fontsize=12)
        plt.ylabel("Model", fontsize=12)
        plt.xlim(0, 100)
        plt.tight_layout()
        plt.savefig(os.path.join(graphs_dir, "fig_1_success_rate.png"), dpi=300)
        plt.close()

        # =========================================================
        # Figure 2: TTR Distribution (Box Plot)
        # =========================================================
        plt.figure(figsize=(10, 6))
        success_df = df[df["passed"] == True]
        if not success_df.empty:
            sns.boxplot(
                data=success_df,
                x="ttr",
                y="model",
                hue="model",
                legend=False,
                palette="mako",
            )
            plt.title(
                "Time To Resolution (TTR) Distribution (Successful Repairs)",
                fontsize=14,
                pad=15,
            )
            plt.xlabel("Seconds", fontsize=12)
            plt.ylabel("Model", fontsize=12)
            plt.tight_layout()
            plt.savefig(os.path.join(graphs_dir, "fig_2_ttr_dist.png"), dpi=300)
        plt.close()

        # =========================================================
        # Figure 3: Category Performance Heatmap
        # =========================================================
        plt.figure(figsize=(12, 7))
        # Create a pivot table: Rows = Models, Columns = Categories, Values = % Passed
        pivot_df = (
            df.pivot_table(
                values="passed", index="model", columns="category", aggfunc="mean"
            )
            * 100
        )
        sns.heatmap(
            pivot_df,
            annot=True,
            cmap="YlGnBu",
            fmt=".0f",
            cbar_kws={"label": "Success Rate (%)"},
        )
        plt.title("Fault Category Success Rate Heatmap", fontsize=14, pad=15)
        plt.xlabel("Fault Category", fontsize=12)
        plt.ylabel("Model Architecture", fontsize=12)
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.savefig(os.path.join(graphs_dir, "fig_3_category_heatmap.png"), dpi=300)
        plt.close()

        # =========================================================
        # Figure 4: Failure Taxonomy Breakdown (Stacked Bar)
        # =========================================================
        fail_df = df[df["passed"] == False].copy()
        if not fail_df.empty:
            plt.figure(figsize=(12, 7))
            # Clean up long failure strings for the legend
            fail_df["failure_reason"] = fail_df["failure_reason"].apply(
                lambda x: str(x).split("(")[0].strip()
            )

            # Count occurrences of each failure reason per model
            fail_counts = (
                fail_df.groupby(["model", "failure_reason"])
                .size()
                .unstack(fill_value=0)
            )

            # Normalize to 100%
            fail_pct = fail_counts.div(fail_counts.sum(axis=1), axis=0) * 100

            # Plot stacked bar chart
            fail_pct.plot(kind="bar", stacked=True, colormap="Set2", figsize=(12, 7))
            plt.title("Failure Taxonomy Breakdown (100% Stacked)", fontsize=14, pad=15)
            plt.xlabel("Model", fontsize=12)
            plt.ylabel("Percentage of Failures (%)", fontsize=12)
            plt.legend(
                title="Primary Cause of Failure",
                bbox_to_anchor=(1.05, 1),
                loc="upper left",
            )
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            plt.savefig(os.path.join(graphs_dir, "fig_4_failure_taxonomy.png"), dpi=300)
            plt.close()

        # =========================================================
        # Figure 5: Cumulative Success over Iterations (CDF)
        # =========================================================
        plt.figure(figsize=(10, 6))
        max_iterations = 15
        iterations_range = range(1, max_iterations + 1)

        for model in df["model"].unique():
            model_df = df[df["model"] == model]
            total_runs = len(model_df)
            model_success_df = model_df[model_df["passed"] == True]

            cumulative_success = []
            for i in iterations_range:
                # How many runs passed taking `i` or fewer iterations?
                count = len(model_success_df[model_success_df["iterations"] <= i])
                cumulative_success.append((count / total_runs) * 100)

            plt.plot(
                iterations_range,
                cumulative_success,
                marker="o",
                linewidth=2,
                label=model,
            )

        plt.title("Cumulative Repair Success by Iteration Count", fontsize=14, pad=15)
        plt.xlabel("Iteration Limit (k)", fontsize=12)
        plt.ylabel("Cumulative Success Rate (%)", fontsize=12)
        plt.xlim(1, max_iterations)
        plt.ylim(0, 105)
        plt.grid(True, linestyle="--", alpha=0.7)
        plt.legend(
            title="Model Architecture", bbox_to_anchor=(1.05, 1), loc="upper left"
        )
        plt.tight_layout()
        plt.savefig(os.path.join(graphs_dir, "fig_5_iteration_cdf.png"), dpi=300)
        plt.close()

        success(f"5 Academic Figures generated successfully in {graphs_dir}")

    except ImportError:
        warning("Pandas/Matplotlib/Seaborn not found. Skipping graph generation.")
        info(
            "Run 'pip install pandas matplotlib seaborn' to enable automatic graphing."
        )
    except Exception as e:
        warning(f"Graph generation failed: {e}")
