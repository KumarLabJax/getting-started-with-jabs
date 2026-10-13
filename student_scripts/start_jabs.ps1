<#
.SYNOPSIS
    One-click start: set up the venv, fetch the course data, open the JABS GUI,
    and load the student notebook.

.DESCRIPTION
    - Creates .venv and installs requirements.txt if they are missing.
    - Activates the venv in the current session.
    - Downloads the Zenodo grooming dataset (~110 MB) on first run, prepares the
      training pool (data/zenodo_no_gt_cached/, without the held-out session) and
      builds the practice set (data/zenodo_scrubbed/): about half the videos keep
      their original labels, the rest are unlabeled for hands-on labeling.
      Features are cached with jabs-init so the GUI opens ready to train. An existing
      practice set is never rebuilt, so labels you made are kept.
    - Launches the JABS GUI in a separate window (venv already active).
    - Starts JupyterLab on student_notebooks/live_demo/jabs-demo.ipynb.

.EXAMPLE
    .\student_scripts\start_jabs.ps1
    .\student_scripts\start_jabs.ps1 -NoGui
    .\student_scripts\start_jabs.ps1 -NoNotebook
    .\student_scripts\start_jabs.ps1 -SkipData     # offline: use the bundled toy data
#>
[CmdletBinding()]
param(
    [switch]$NoGui,
    [switch]$NoNotebook,
    [switch]$SkipData,
    [string]$Notebook = "student_notebooks/live_demo/jabs-demo.ipynb"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvDir = Join-Path $RepoRoot ".venv"
$Activate = Join-Path $VenvDir "Scripts\Activate.ps1"
$Requirements = Join-Path $RepoRoot "requirements.txt"
$NotebookPath = Join-Path $RepoRoot $Notebook

Set-Location $RepoRoot

# 1. Create the venv if needed
if (-not (Test-Path $Activate)) {
    Write-Host "[INFO] No venv found. Creating .venv ..."
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }
    if (-not $py) {
        Write-Host "[MISSING] Python was not found on PATH. Install Python 3.10+ and retry."
        exit 1
    }
    & $py.Source -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { Write-Host "[WARN] venv creation failed."; exit 1 }
}

# 2. Activate
& $Activate
Write-Host "[OK] venv activated: $VenvDir"

# 3. Install dependencies if JABS or Jupyter is missing
$ScriptsDir = Join-Path $VenvDir "Scripts"
$jabsInstalled = (Get-ChildItem -Path $ScriptsDir -Filter "jabs*.exe" -ErrorAction SilentlyContinue) -ne $null
$jupyterInstalled = Test-Path (Join-Path $ScriptsDir "jupyter-lab.exe")
if (-not ($jabsInstalled -and $jupyterInstalled)) {
    Write-Host "[INFO] Installing requirements (first run can take several minutes) ..."
    python -m pip install --upgrade pip
    python -m pip install -r $Requirements
    if ($LASTEXITCODE -ne 0) { Write-Host "[WARN] pip install failed."; exit 1 }
}

# 4. Course data: download if missing, prepare the training pool, build the practice set if
#    missing, and cache features with jabs-init, all in one script (safe to re-run)
if (-not $SkipData) {
    python student_scripts/prepare_course_data.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[WARN] Course data is not ready. Continuing with the bundled toy data; rerun to retry."
    }
}

# 5. Launch the JABS GUI in its own window
if (-not $NoGui) {
    $guiExe = Join-Path $ScriptsDir "jabs-gui.exe"
    if (-not (Test-Path $guiExe)) { $guiExe = Join-Path $ScriptsDir "jabs.exe" }
    if (Test-Path $guiExe) {
        Write-Host "[INFO] Opening JABS GUI ..."
        Start-Process -FilePath $guiExe -WorkingDirectory $RepoRoot
    }
    else {
        Write-Host "[WARN] JABS GUI launcher not found in $ScriptsDir. Skipping."
    }
}

# 6. Open the student notebook in JupyterLab (blocks until Jupyter is stopped)
if (-not $NoNotebook) {
    if (-not (Test-Path $NotebookPath)) {
        Write-Host "[MISSING] Notebook not found: $NotebookPath"
        exit 1
    }
    Write-Host "[INFO] Opening notebook in JupyterLab (Ctrl+C to stop) ..."
    python -m jupyterlab $NotebookPath
}
