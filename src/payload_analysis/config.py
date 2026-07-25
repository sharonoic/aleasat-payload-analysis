import os
from pathlib import Path

# Repo root = two levels up from this file (src/payload_analysis/config.py)
REPO_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = Path(os.environ.get("ALEASAT_DATA_DIR", REPO_ROOT / "data"))
RESULTS_DIR = Path(os.environ.get("ALEASAT_RESULTS_DIR", REPO_ROOT / "results"))

RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Calibration constants from fit_focus_curve(), mapping a measured focus
# metric back to an estimated blur sigma (px). Fitted against a known-sigma
# synthetic blur series -- see payload_analysis.validation.
#
# Model: f(sigma) = A * exp(-k * sigma) + C
# Re-run payload_analysis.validation.fit_focus_curve() and update these if
# the calibration source image changes.
SIGMA_CALIBRATION = {
    "focus_metric": {"A": 0.0169, "k": 1.7216, "C": -0.0001},
    "log_focus_score": {"A": 64.9995, "k": 0.6504, "C": -0.0604},
    "focus_score": {"A": 64.9995, "k": 0.6504, "C": -0.0604}, 

}

# Temperature mapping for TVAC thermal-cycle test folders -> operating temp (C).
# Move new test-folder-name -> temp mappings here as new runs are added,
# instead of editing plotting code.
TEMP_MAP = {
    "CYCLE1_MIN_OP_20260623-1347": -18,   # -17 to -19C, midpoint
    "CYCLE2_MAX_OP_20260623-1550": 40,
    "CYCLE2_MIN_OP_20260623-1948": -18,   # -17 to -19C
    "CYCLE3_MAX_OP_20260623-2226": 40,
    "CYCLE3_MIN_OP_20260624-1024": -18,   # -17 to -19C
    "STRESS_MIN_OP_20260626-1018": -8,    # TRP = -8C
    "THERMAL_MIN_OP_20260625-1317": -2,   # -3 to -1C, midpoint
    "TVACOFF_20260626-1236": 30,
    # 'CYCLE1_MAX_OP_20260623-1055': 41,  # left disabled in original script - 40-42C
}
