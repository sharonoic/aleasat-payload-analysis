import os
from pathlib import Path

# Repo root = two levels up from this file (src/payload_analysis/config.py)
REPO_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = Path(os.environ.get("ALEASAT_DATA_DIR", REPO_ROOT / "data"))
RESULTS_DIR = Path(os.environ.get("ALEASAT_RESULTS_DIR", REPO_ROOT / "results"))

RESULTS_DIR.mkdir(parents=True, exist_ok=True)

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
