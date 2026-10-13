#!/usr/bin/env bash
# One-click start for macOS and Linux: set up the venv, fetch the course data,
# open the JABS GUI, and load the student notebook.
#
#   ./student_scripts/start_jabs.sh
#   ./student_scripts/start_jabs.sh --no-gui
#   ./student_scripts/start_jabs.sh --no-notebook
#   ./student_scripts/start_jabs.sh --skip-data     # offline: use the bundled toy data
#
# Same steps as start_jabs.ps1 (Windows).
set -euo pipefail

NOTEBOOK="student_notebooks/live_demo/jabs-demo.ipynb"
NO_GUI=0
NO_NOTEBOOK=0
SKIP_DATA=0
for arg in "$@"; do
    case "$arg" in
        --no-gui) NO_GUI=1 ;;
        --no-notebook) NO_NOTEBOOK=1 ;;
        --skip-data) SKIP_DATA=1 ;;
        -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
        *) echo "[WARN] Unknown option: $arg" ;;
    esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv"
cd "$REPO_ROOT"


# 0. macOS: XGBoost needs libomp
if [ "$(uname -s)" = "Darwin" ] && command -v brew > /dev/null 2>&1; then
    if ! brew list libomp > /dev/null 2>&1; then
        echo "[INFO] Installing libomp (XGBoost requirement) ..."
        brew install libomp || echo "[WARN] 'brew install libomp' failed; install it manually."
    fi
fi

# 1. Create the venv if needed
if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "[INFO] No venv found. Creating .venv ..."
    PY="$(command -v python3 || command -v python || true)"
    if [ -z "$PY" ]; then
        echo "[MISSING] Python was not found on PATH. Install Python 3.10+ and retry."
        exit 1
    fi
    "$PY" -m venv "$VENV_DIR"
fi

# 2. Activate
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
echo "[OK] venv activated: $VENV_DIR"

# 3. Install dependencies if JABS or Jupyter is missing
if ! { command -v jabs > /dev/null 2>&1 && command -v jupyter-lab > /dev/null 2>&1; }; then
    echo "[INFO] Installing requirements (first run can take several minutes) ..."
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
fi

# 4. Course data: download if missing, prepare the training pool, build the practice set if
#    missing, and cache features with jabs-init, all in one script (safe to re-run)
if [ "$SKIP_DATA" -eq 0 ]; then
    python student_scripts/prepare_course_data.py || echo "[WARN] Course data is not ready. Continuing with the bundled toy data; rerun to retry."
fi

# 5. Launch the JABS GUI in the background
if [ "$NO_GUI" -eq 0 ]; then
    if command -v jabs > /dev/null 2>&1; then
        echo "[INFO] Opening JABS GUI ..."
        nohup jabs > /dev/null 2>&1 &
    else
        echo "[WARN] 'jabs' launcher not found in the venv. Skipping."
    fi
fi

# 6. Open the student notebook in JupyterLab (blocks until Jupyter is stopped)
if [ "$NO_NOTEBOOK" -eq 0 ]; then
    if [ ! -f "$NOTEBOOK" ]; then
        echo "[MISSING] Notebook not found: $NOTEBOOK"
        exit 1
    fi
    echo "[INFO] Opening notebook in JupyterLab (Ctrl+C to stop) ..."
    python -m jupyterlab "$NOTEBOOK"
fi
