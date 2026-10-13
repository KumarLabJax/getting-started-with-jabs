# Environment Setup

## Requirements

- Python 3.10–3.12
- ~2 GB disk space for toy data and dependencies
- ~1.5 GB disk space for the Zenodo `jabs_grooming` download and the practice set with its cached features (optional beyond toy data)
- ~50 GB disk space for the full Harvard Dataverse dataset (optional deep dive)

## Connecting to a remote course computer

If your course computer is remote, connect with **Windows App** on a Mac, or **Remote Desktop (RDP)** on Windows.

## Installation

```bash
# 1. Clone the repo
git clone git@github.com:KumarLabJax/getting-started-with-jabs.git
cd getting-started-with-jabs

# 2. Create a virtual environment
python -m venv .venv

# 3. Activate it
#    macOS / Linux:
source .venv/bin/activate
#    Windows:
.venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Verify the install
python student_scripts/verify_environment.py
```

All checks should show `[OK]`. If any show `[MISSING]` or `[OUTDATED]`, follow the fix
instructions printed by the script.

## macOS note (XGBoost / OpenMP)

JABS uses XGBoost, which requires OpenMP on macOS:

```bash
brew install libomp
```

## Starting JupyterLab

```bash
jupyter lab
```

Open `student_notebooks/live_demo/jabs-demo.ipynb`, the one notebook you run (the one-click launchers open it for you). The course pages `static_build_notebooks/00` to `05` are read-only reading and are published as the course site.

## Downloading course data

The hands-on exercise (notebook 04) runs on the Zenodo JABS example dataset:

```bash
python student_scripts/download_zenodo.py --files jabs_grooming.zip --extract
```

This downloads into `data/zenodo/jabs_grooming/`. Files already present are skipped.

The one-click launchers (`start_jabs`) do all of this for you through
`python student_scripts/prepare_course_data.py`, which you can also run by hand. It downloads the data
if it is missing, builds the practice set in `data/zenodo_scrubbed/` if it does not exist (10 sessions;
the held-out test session, 2010, is never in it), and runs `jabs-init` so features are cached before the
JABS GUI opens. Instructors who rebuild the fallback classifier use `student_scripts/prepare_training_set.py`
instead, which makes `data/zenodo_no_gt_cached/` (all sessions but 2010). An existing practice set is
never rebuilt, so labels you made are kept. None of these folders are committed.
See `config/zenodo/annotation_sets.yaml` for what's selected.

## Downloading the optional full dataset

```bash
python student_scripts/download_dataverse.py
```

This downloads from Harvard Dataverse (`doi:10.7910/DVN/SAPNJG`) into `data/dataverse/`. Files
already present are skipped. See `student_scripts/manifest.json` for the file list - it ships
with a small working example; edit it to add more files.
