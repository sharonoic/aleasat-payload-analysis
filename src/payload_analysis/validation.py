import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
from scipy import ndimage
from scipy.optimize import curve_fit

from .config import RESULTS_DIR
from .metrics import analyze_payload_image, log_focus_score

# Default sigma levels (pixels). 0 = perfectly sharp (unmodified source).
# Spacing is deliberately uneven -- finer steps near 0 where focus metrics
# are most sensitive, coarser steps at high blur where most metrics saturate.
DEFAULT_SIGMAS = [0, 0.5, 1, 2, 3, 4, 6, 8, 12, 16]


def generate_blur_series(source_image, output_dir, sigmas=None):
    """
    Create a set of images blurred at known Gaussian sigma values from one
    sharp source image.

    Args:
        source_image: path to a single sharp reference image
        output_dir: directory to write blurred images into (created if needed)
        sigmas: list of Gaussian blur sigma values in pixels. Defaults to
                DEFAULT_SIGMAS. sigma=0 just copies the original unmodified.

    Returns:
        DataFrame with columns: filename, sigma, filepath
    """
    sigmas = sigmas if sigmas is not None else DEFAULT_SIGMAS
    source_image = Path(source_image)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    img = Image.open(source_image).convert("RGB")
    img_array = np.array(img, dtype=np.float32)

    rows = []
    for sigma in sigmas:
        if sigma == 0:
            blurred = img_array
        else:
            # sigma=0 on the channel axis so RGB channels aren't blurred together
            blurred = ndimage.gaussian_filter(img_array, sigma=(sigma, sigma, 0))

        blurred_img = Image.fromarray(np.clip(blurred, 0, 255).astype(np.uint8))
        filename = f"sigma_{sigma:04.1f}.jpg".replace(".", "p", 1)  # e.g. sigma_02p0.jpg
        filepath = output_dir / filename
        blurred_img.save(filepath, quality=95)

        rows.append({"filename": filename, "sigma": sigma, "filepath": str(filepath)})
        print(f"  Wrote {filename} (sigma={sigma})")

    manifest = pd.DataFrame(rows)
    manifest_path = output_dir / "manifest.csv"
    manifest.to_csv(manifest_path, index=False)
    print(f"\nManifest saved to {manifest_path}")

    return manifest


def validate_focus_metrics(blur_series_dir, output_csv=None):
    """
    Run both focus metrics (Laplacian-variance based, and LoG-based) against
    a known-sigma blur series and plot the result. A correctly-working focus
    metric should decrease monotonically as sigma increases.

    Args:
        blur_series_dir: directory created by generate_blur_series
                          (must contain manifest.csv)
        output_csv: where to save results (default: RESULTS_DIR / 'blur_validation_results.csv')

    Returns:
        DataFrame with sigma, focus_metric, sharpness, astigmatism_ratio, log_focus_score
    """
    blur_series_dir = Path(blur_series_dir)
    manifest = pd.read_csv(blur_series_dir / "manifest.csv")

    results = []
    for _, row in manifest.iterrows():
        metrics = analyze_payload_image(row["filepath"])
        metrics["log_focus_score"] = log_focus_score(row["filepath"])
        metrics["sigma"] = row["sigma"]
        metrics["filename"] = row["filename"]
        results.append(metrics)

    df = pd.DataFrame(results).sort_values("sigma").reset_index(drop=True)

    if output_csv is None:
        output_csv = RESULTS_DIR / "blur_validation_results.csv"
    df.to_csv(output_csv, index=False)
    print(f"Results saved to {output_csv}")

    # Sanity check: is focus_metric monotonically non-increasing with sigma?
    is_monotonic = (df["focus_metric"].diff().dropna() <= 1e-9).all()
    print(f"\nfocus_metric monotonically decreasing with sigma: {is_monotonic}")
    if not is_monotonic:
        print("  -> Check the printed table below for where it breaks:")
        print(df[["sigma", "focus_metric"]].to_string(index=False))

    _plot_validation(df)

    return df


def _exp_decay(sigma, A, k, C):
    """f(sigma) = A * exp(-k*sigma) + C -- the model shape used by fit_focus_curve."""
    return A * np.exp(-k * sigma) + C


def fit_focus_curve(df, column="focus_metric"):
    """
    Fit an exponential decay curve to a focus metric as a function of known
    blur sigma: f(sigma) = A * exp(-k*sigma) + C

    A = value at sigma=0 (in-focus) minus the floor C
    k = decay rate -- larger k means the metric loses sensitivity to blur
        faster (saturates sooner); smaller k means it stays informative
        across a wider blur range
    C = floor/asymptote value the metric approaches at heavy blur

    Args:
        df: DataFrame with a 'sigma' column and the metric column to fit
            (as returned by validate_focus_metrics)
        column: which column to fit -- typically 'focus_metric' or 'log_focus_score'

    Returns:
        dict with keys: A, k, C, r_squared, predict (a callable: predict(sigma) -> value)
    """
    sigma = df["sigma"].values.astype(float)
    y = df[column].values.astype(float)

    # Initial guesses: A ~ value range, k ~ 1, C ~ minimum observed value
    p0 = [y.max() - y.min(), 1.0, y.min()]
    popt, _ = curve_fit(_exp_decay, sigma, y, p0=p0, maxfev=10000)
    A, k, C = popt

    y_pred = _exp_decay(sigma, *popt)
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")

    print(f"Fit for '{column}': f(sigma) = {A:.4f} * exp(-{k:.4f} * sigma) + {C:.4f}")
    print(f"  R^2 = {r_squared:.4f}")

    return {
        "A": A,
        "k": k,
        "C": C,
        "r_squared": r_squared,
        "predict": lambda sigma_val: _exp_decay(np.asarray(sigma_val, dtype=float), A, k, C),
    }


def plot_focus_curve_fit(df, column="focus_metric", fit=None, ax=None):
    """
    Plot measured data points for a focus metric against sigma, with the
    fitted exponential curve overlaid.

    Args:
        df: DataFrame with 'sigma' and the metric column
        column: which column to plot/fit
        fit: optional pre-computed fit dict from fit_focus_curve (fits fresh if None)
        ax: optional matplotlib axis to plot into (creates a new figure if None)

    Returns:
        the fit dict used
    """
    if fit is None:
        fit = fit_focus_curve(df, column=column)

    sigma = df["sigma"].values.astype(float)
    y = df[column].values.astype(float)
    sigma_smooth = np.linspace(sigma.min(), sigma.max(), 200)

    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=(7, 5))

    ax.scatter(sigma, y, s=70, color="blue", zorder=3, label="measured")
    ax.plot(
        sigma_smooth, fit["predict"](sigma_smooth), "--", color="red", linewidth=2,
        label=f"fit: {fit['A']:.3g}·e^(-{fit['k']:.3g}σ)+{fit['C']:.3g}  (R²={fit['r_squared']:.3f})",
    )
    ax.set_title(f"{column} vs. blur sigma", fontsize=12, fontweight="bold")
    ax.set_xlabel("Gaussian blur sigma (px) -- ground truth", fontsize=11)
    ax.set_ylabel(column, fontsize=11)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    if standalone:
        plt.tight_layout()
        plt.show()

    return fit

def estimate_sigma(value, fit):
    """
    Invert a fitted focus curve to estimate blur sigma from a measured
    focus metric value. Given f(sigma) = A*exp(-k*sigma) + C, solving for
    sigma gives:
 
        sigma = -ln((value - C) / A) / k
 
    This lets you take real, unlabeled captures (with unknown actual
    defocus) and convert their focus_metric/log_focus_score into an
    estimated "equivalent blur sigma" in the same units as your synthetic
    calibration set -- useful for expressing real focus degradation in
    physically interpretable terms.
 
    Args:
        value: measured focus metric value (scalar, list, or array)
        fit: a fit dict from fit_focus_curve (must contain A, k, C)
 
    Returns:
        estimated sigma (same shape as value). Returns np.nan where the
        measured value is at/below the curve's floor C -- meaning the
        image is blurred beyond what the calibration curve can resolve,
        so no sigma estimate is meaningful there.
    """
    value = np.asarray(value, dtype=float)
    ratio = (value - fit["C"]) / fit["A"]
    with np.errstate(invalid="ignore", divide="ignore"):
        sigma = -np.log(ratio) / fit["k"]
    sigma = np.where(ratio > 0, sigma, np.nan)
    return sigma
 

def apply_sigma_estimate(df, fit, column, new_column="estimated_sigma"):
    """
    Apply estimate_sigma across a DataFrame column of real (unlabeled)
    focus metric measurements, adding an estimated blur sigma column.
 
    Args:
        df: DataFrame containing the metric column to convert
        fit: a fit dict from fit_focus_curve (the calibration curve)
        column: name of the column with measured focus metric values
        new_column: name for the new estimated-sigma column
 
    Returns:
        df with new_column added (a copy, original is not modified)
    """
    df = df.copy()
    df[new_column] = estimate_sigma(df[column].values, fit)
    return df
 
 
def plot_sigma_estimates(df, group_col=None, sigma_col="estimated_sigma", title=None):
    """
    Plot estimated blur sigma for a set of real captures, one point per row
    (or averaged per group if group_col is given, e.g. 'subdir').
 
    Args:
        df: DataFrame with an estimated sigma column (from apply_sigma_estimate)
        group_col: optional column to group/average by (e.g. 'subdir', 'temperature')
        sigma_col: name of the estimated sigma column to plot
        title: optional plot title
    """
    fig, ax = plt.subplots(figsize=(10, 6))
 
    if group_col:
        grouped = df.groupby(group_col)[sigma_col].agg(["mean", "std"]).reset_index()
        ax.errorbar(
            grouped[group_col], grouped["mean"], yerr=grouped["std"],
            fmt="o", markersize=8, capsize=4, color="darkorange", ecolor="gray",
        )
        ax.set_xlabel(group_col, fontsize=11)
        plt.xticks(rotation=45, ha="right")
    else:
        ax.scatter(range(len(df)), df[sigma_col], s=60, color="darkorange")
        ax.set_xlabel("Image index", fontsize=11)
 
    ax.set_ylabel("Estimated blur sigma (px, calibrated)", fontsize=11)
    ax.set_title(title or "Estimated blur sigma for real captures", fontsize=12, fontweight="bold")
    ax.grid(True, alpha=0.3)
 
    plt.tight_layout()
    plt.show()
 

def _plot_validation(df):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    axes[0].plot(df["sigma"], df["focus_metric"], marker="o", linewidth=2,
                 markersize=8, color="blue")
    axes[0].set_title("Laplacian-Variance Focus Metric vs. Known Blur Sigma",
                       fontsize=12, fontweight="bold")
    axes[0].set_xlabel("Gaussian blur sigma (px) -- ground truth", fontsize=11)
    axes[0].set_ylabel("focus_metric (higher = sharper)", fontsize=11)
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(df["sigma"], df["log_focus_score"], marker="s", linewidth=2,
                 markersize=8, color="purple")
    axes[1].set_title("LoG Focus Score vs. Known Blur Sigma",
                       fontsize=12, fontweight="bold")
    axes[1].set_xlabel("Gaussian blur sigma (px) -- ground truth", fontsize=11)
    axes[1].set_ylabel("log_focus_score (higher = sharper)", fontsize=11)
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


def _main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Path to a sharp source image")
    parser.add_argument("--output", default=None,
                         help="Output directory (default: DATA_DIR/blur_validation)")
    parser.add_argument("--sigmas", nargs="+", type=float, default=None,
                         help=f"Blur sigma values (default: {DEFAULT_SIGMAS})")
    args = parser.parse_args()

    from .config import DATA_DIR
    output_dir = Path(args.output) if args.output else DATA_DIR / "blur_validation"

    generate_blur_series(args.source, output_dir, sigmas=args.sigmas)
    validate_focus_metrics(output_dir)


if __name__ == "__main__":
    _main()