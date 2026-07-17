# ALEASAT Payload Functional Test Analysis

Focus / sharpness / astigmatism analysis for payload camera functional test
captures (pre/post-vibe, TVAC thermal cycling).

## Structure

```
.
├── src/payload_analysis/   # reusable functions — the actual logic
│   ├── metrics.py          # per-image metrics (focus, sharpness, astigmatism, LoG focus score)
│   ├── batch.py            # directory/batch processing + CSV output
│   ├── plotting.py         # all plotting functions
│   └── config.py           # paths + temperature mapping (edit this, not the code)
├── notebooks/
│   └── ETC_func_test_analysis.ipynb   # run log: imports src/, calls functions, shows plots
├── data/                    # NOT in git — put your capture folders here
└── results/                 # NOT in git — generated CSVs land here
```

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Data

Image captures are **not** committed to this repo (`data/` and `results/`
are gitignored — binary image data bloats git history permanently).

```
data/
├── 260609_pre_vibe_func_test/
│   ├── angle-0/*.jpg
│   └── angle-90/*.jpg
└── New TRP/
    ├── CYCLE1_MIN_OP_20260623-1347/*.jpg
    └── ...
```

## Usage

Open `notebooks/ETC_func_test_analysis.ipynb` and run top to bottom, or
import functions directly:

```python
from payload_analysis import analyze_payload_directory, plot_payload_metrics

df = analyze_payload_directory('data/260609_pre_vibe_func_test')
plot_payload_metrics('results/260609_pre_vibe_func_test_all_metrics.csv')
```

## Adding a new temperature-mapped test run

Edit `TEMP_MAP` in `src/payload_analysis/config.py` — don't edit the
plotting code.
