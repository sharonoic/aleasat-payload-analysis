from pathlib import Path

import pandas as pd

from .config import RESULTS_DIR, SIGMA_CALIBRATION
from .metrics import analyze_payload_image, log_focus_score
from .validation import apply_sigma_estimate, plot_sigma_estimates



def analyze_payload_directory(master_dir, output_csv=None, per_subdir=False):
    """
    Process all images in all subdirectories of master_dir using
    analyze_payload_image (focus/sharpness/astigmatism metrics).

    Args:
        master_dir: path to a test-run directory containing subdirs
        output_csv: output CSV path (default: RESULTS_DIR / f"{name}_all_metrics.csv")
        per_subdir: if True, save + return a separate DataFrame per subdirectory
                    instead of one combined DataFrame

    Returns:
        DataFrame with results, or dict[subdir_name -> DataFrame] if per_subdir=True
    """
    master_dir = Path(master_dir)
    subdirs = sorted(d for d in master_dir.iterdir() if d.is_dir())

    if not subdirs:
        print(f"No subdirectories found in {master_dir}")
        return None

    all_results = []
    dataframes = {}

    for subdir in subdirs:
        images = sorted(subdir.glob("*.jpg")) + sorted(subdir.glob("*.png"))
        if not images:
            print(f"  No images in {subdir.name}")
            continue

        print(f"Processing {subdir.name}...")
        subdir_results = []
        for img_path in images:
            result = analyze_payload_image(str(img_path))
            result["subdir"] = subdir.name
            subdir_results.append(result)

        if subdir_results:
            if per_subdir:
                df = pd.DataFrame(subdir_results)
                csv_path = RESULTS_DIR / f"{subdir.name}_metrics.csv"
                df.to_csv(csv_path, index=False)
                print(f"  Saved: {csv_path}")
                dataframes[subdir.name] = df
            else:
                all_results.extend(subdir_results)

    if per_subdir:
        return dataframes

    if not all_results:
        print("No results collected")
        return None

    df = pd.DataFrame(all_results)
    if output_csv is None:
        output_csv = RESULTS_DIR / f"{master_dir.name}_all_metrics.csv"
    df.to_csv(output_csv, index=False)
    print(f"\nAll results saved to {output_csv}")

    return df


def compute_focus_scores(master_dir, output_csv=None):
    """
    Compute LoG-based focus scores for all images in subdirectories of
    master_dir. Independent cross-check against analyze_payload_directory.

    Args:
        master_dir: path to a test-run directory containing subdirs
        output_csv: output CSV path (default: RESULTS_DIR / f"{name}_focus_scores.csv")

    Returns:
        DataFrame with filename, subdir, focus_score
    """
    master_dir = Path(master_dir)
    subdirs = sorted(d for d in master_dir.iterdir() if d.is_dir())

    results = []
    for subdir in subdirs:
        images = sorted(subdir.glob("*.jpg")) + sorted(subdir.glob("*.png"))
        if not images:
            print(f"No images in {subdir.name}")
            continue

        print(f"Processing {subdir.name}...")
        for img_path in images:
            try:
                score = log_focus_score(img_path)
                results.append({
                    "filename": img_path.name,
                    "subdir": subdir.name,
                    "focus_score": score,
                })
            except Exception as e:
                print(f"  Error processing {img_path.name}: {e}")

    df = pd.DataFrame(results)
    if output_csv is None:
        output_csv = RESULTS_DIR / f"{master_dir.name}_focus_scores.csv"
    df.to_csv(output_csv, index=False)
    print(f"\nFocus scores saved to {output_csv}")

    return df


def analyze_astigmatism_by_angle(csv_path):
    """
    Check whether astigmatism ratio is consistent across angles.

    High variance across angles for a fixed target -> likely target tilt.
    Low variance -> likely genuine optical astigmatism.

    Args:
        csv_path: path to a metrics CSV with 'angle' and 'astigmatism_ratio' columns
    """
    df = pd.read_csv(csv_path)

    if "angle" not in df.columns:
        if "subdir" not in df.columns:
            raise ValueError(
                "CSV has neither an 'angle' nor a 'subdir' column. Cannot analyze astigmatism by angle."
            )
        df["angle"] = df["subdir"].str.extract(r"(\d+)").astype(int)

    print("Astigmatism by angle:")
    print(df[["angle", "astigmatism_ratio"]])
    print(f"\nMean: {df['astigmatism_ratio'].mean():.3f}")
    print(f"Std dev: {df['astigmatism_ratio'].std():.3f}")

    if df["astigmatism_ratio"].std() > 0.05:
        print("-> High variance: likely target tilt, not optical astigmatism")
    else:
        print("-> Low variance: likely optical astigmatism")

    return df

def estimate_sigma_for_run(csv_path, metric="focus_metric", calibration=None,
                            group_col="subdir", output_csv=None, plot=True):
    """
    Apply the sigma calibration curve backwards to a real (unlabeled) metrics
    CSV -- converting each row's measured focus metric into an estimated
    blur sigma, then optionally plotting it grouped by subdir.
 
    This runs the calibration "in reverse": fit_focus_curve() in
    validation.py is fit on a known-sigma synthetic series; this function
    applies that fitted curve to real captures where the true sigma is
    unknown, to estimate what it likely was.
 
    Args:
        csv_path: path to a metrics CSV produced by analyze_payload_directory
                  or compute_focus_scores (must contain the `metric` column)
        metric: which column to convert -- 'focus_metric' or 'log_focus_score'
        calibration: optional override dict with A/k/C. Defaults to
                     config.SIGMA_CALIBRATION[metric]
        group_col: column to group/average by when plotting (default 'subdir')
        output_csv: where to save the result (default: csv_path with
                    '_with_sigma' appended before the extension)
        plot: if True, also calls plot_sigma_estimates on the result
 
    Returns:
        DataFrame with an added 'estimated_sigma' column
    """
    df = pd.read_csv(csv_path)
 
    if metric not in df.columns:
        raise ValueError(
            f"Column '{metric}' not found in {csv_path}. Available columns: {list(df.columns)}"
        )
 
    calibration = calibration or SIGMA_CALIBRATION.get(metric)
    if calibration is None:
        raise ValueError(
            f"No calibration available for '{metric}'. Pass one explicitly via "
            f"the calibration= argument, or add it to config.SIGMA_CALIBRATION."
        )
 
    df = apply_sigma_estimate(df, calibration, metric)
 
    csv_path = Path(csv_path)
    if output_csv is None:
        output_csv = csv_path.with_name(csv_path.stem + "_with_sigma" + csv_path.suffix)
    df.to_csv(output_csv, index=False)
    print(f"Saved sigma estimates to {output_csv}")
 
    n_unresolved = df["estimated_sigma"].isna().sum()
    if n_unresolved:
        print(f"  Note: {n_unresolved}/{len(df)} rows blurred beyond calibration range (estimated_sigma = NaN)")
 
    if plot and group_col in df.columns:
        plot_sigma_estimates(
            df, group_col=group_col, sigma_col="estimated_sigma",
            title=f"Estimated blur sigma ({metric}) -- {csv_path.stem}",
        )
 
    return df
 
