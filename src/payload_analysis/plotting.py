from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .config import TEMP_MAP


def plot_payload_metrics(csv_path):
    """
    Plot focus_metric / sharpness / astigmatism_ratio from a single test-run
    CSV, one point per subdirectory.
    """
    df = pd.read_csv(csv_path)
    csv_name = Path(csv_path).stem

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle(csv_name, fontsize=14, fontweight="bold", y=1.02)

    axes[0].scatter(df["subdir"], df["focus_metric"], s=150, alpha=0.7,
                     color="blue", edgecolors="black", linewidth=1.5)
    axes[0].set_title("Focus Metric (Laplacian Variance)", fontsize=12, fontweight="bold")
    axes[0].set_ylabel("Variance", fontsize=11)
    axes[0].set_xlabel("Subdirectory", fontsize=11)
    axes[0].tick_params(axis="x", rotation=45)
    axes[0].grid(True, alpha=0.3)

    axes[1].scatter(df["subdir"], df["sharpness"], s=150, alpha=0.7,
                     color="green", edgecolors="black", linewidth=1.5)
    axes[1].set_title("Sharpness (Mean Gradient)", fontsize=12, fontweight="bold")
    axes[1].set_ylabel("Mean Gradient", fontsize=11)
    axes[1].set_xlabel("Subdirectory", fontsize=11)
    axes[1].tick_params(axis="x", rotation=45)
    axes[1].grid(True, alpha=0.3)

    axes[2].scatter(df["subdir"], df["astigmatism_ratio"], s=150, alpha=0.7,
                     color="red", edgecolors="black", linewidth=1.5)
    axes[2].axhline(y=1.0, color="gray", linestyle="--", linewidth=1.5, label="No astigmatism")
    axes[2].set_title("Astigmatism Ratio (H/V)", fontsize=12, fontweight="bold")
    axes[2].set_ylabel("Ratio", fontsize=11)
    axes[2].set_xlabel("Subdirectory", fontsize=11)
    axes[2].tick_params(axis="x", rotation=45)
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


def plot_payload_metrics_timeline(csv_paths):
    """
    Plot focus_metric / sharpness / astigmatism_ratio averaged per test run,
    across multiple test-run CSVs in chronological order.

    Args:
        csv_paths: list of CSV paths, chronological order

    Returns:
        DataFrame with one row per test run (averaged metrics)
    """
    timeline_data = []
    for csv_path in csv_paths:
        df = pd.read_csv(csv_path)
        csv_name = Path(csv_path).stem
        timeline_data.append({
            "test_name": csv_name,
            "focus_metric": df["focus_metric"].mean(),
            "sharpness": df["sharpness"].mean(),
            "astigmatism_ratio": df["astigmatism_ratio"].mean(),
        })

    timeline_df = pd.DataFrame(timeline_data)
    x = range(len(timeline_df))

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    axes[0].plot(x, timeline_df["focus_metric"], marker="o", linewidth=2,
                 markersize=10, color="blue", label="Focus Metric")
    axes[0].scatter(x, timeline_df["focus_metric"], s=150, color="blue",
                     edgecolors="black", linewidth=1.5, zorder=3)
    axes[0].set_title("Focus Metric Over Time (Higher = Better)", fontsize=12, fontweight="bold")
    axes[0].set_ylabel("Laplacian Variance", fontsize=11)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(timeline_df["test_name"], rotation=45, ha="right")
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(x, timeline_df["sharpness"], marker="s", linewidth=2,
                 markersize=10, color="green", label="Sharpness")
    axes[1].scatter(x, timeline_df["sharpness"], s=150, color="green",
                     edgecolors="black", linewidth=1.5, zorder=3)
    axes[1].set_title("Sharpness Over Time (Higher = Better)", fontsize=12, fontweight="bold")
    axes[1].set_ylabel("Mean Gradient", fontsize=11)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(timeline_df["test_name"], rotation=45, ha="right")
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(x, timeline_df["astigmatism_ratio"], marker="^", linewidth=2,
                 markersize=10, color="red", label="Astigmatism")
    axes[2].scatter(x, timeline_df["astigmatism_ratio"], s=150, color="red",
                     edgecolors="black", linewidth=1.5, zorder=3)
    axes[2].axhline(y=1.0, color="green", linestyle="--", linewidth=2, label="Perfect (1.0)")
    axes[2].set_title("Astigmatism Over Time (Lower = Better)", fontsize=12, fontweight="bold")
    axes[2].set_ylabel("H/V Ratio", fontsize=11)
    axes[2].set_xticks(x)
    axes[2].set_xticklabels(timeline_df["test_name"], rotation=45, ha="right")
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

    return timeline_df


def plot_focus_scores(df):
    """Plot LoG focus_score by subdirectory (from compute_focus_scores)."""
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.scatter(df["subdir"], df["focus_score"], s=200, alpha=0.6,
               color="purple", edgecolors="black", linewidth=1.5)
    ax.set_title("LoG Focus Scores by Test Configuration", fontsize=14, fontweight="bold")
    ax.set_ylabel("Focus Score (99.9% LoG Quantile)", fontsize=12)
    ax.set_xlabel("Subdirectory", fontsize=12)
    ax.tick_params(axis="x", rotation=45)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


def add_temperatures_and_plot(df, temp_map=None):
    """
    Map temperature data (config.TEMP_MAP by default) onto test folders and
    plot focus_score vs. temperature with a linear fit.

    Args:
        df: DataFrame from compute_focus_scores (needs 'subdir', 'focus_score')
        temp_map: optional override dict of {subdir_name: temp_C}

    Returns:
        DataFrame with added 'temperature' column, unmapped rows dropped
    """
    temp_map = temp_map or TEMP_MAP
    df = df.copy()
    df["temperature"] = df["subdir"].map(temp_map)
    df = df.dropna(subset=["temperature"])

    fig, ax = plt.subplots(figsize=(12, 7))
    ax.scatter(df["temperature"], df["focus_score"], s=200, alpha=0.6,
               color="darkorange", edgecolors="black", linewidth=1.5)

    z = np.polyfit(df["temperature"], df["focus_score"], 1)
    p = np.poly1d(z)
    temp_range = np.linspace(df["temperature"].min(), df["temperature"].max(), 100)
    ax.plot(temp_range, p(temp_range), "r--", linewidth=2,
             label=f"Fit: y={z[0]:.3f}x+{z[1]:.1f}")

    ax.set_title("Focus Score vs Operating Temperature", fontsize=14, fontweight="bold")
    ax.set_xlabel("Temperature (\u00b0C)", fontsize=12)
    ax.set_ylabel("Focus Score (99.9% LoG Quantile)", fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=11)

    plt.tight_layout()
    plt.show()

    return df
