"""Build the fallback grooming classifier and its training report for the live demo notebook.

The notebook expects students to train a classifier in the JABS GUI. If a student has none
(they skipped the labeling break, or the notebook runs unattended), it falls back to the
classifier shipped in data/pretrained/, trained on every labeled session of the full Zenodo
grooming deposit except the held-out dense ground-truth session (2010), together with the
training report JABS wrote for it (the cross-validation table the session walks through).

Shipped files (committed to the repo):
    data/pretrained/grooming_zenodo_full.pickle               the classifier
    data/pretrained/grooming_zenodo_full_training_report.md   the GUI's training report

The training pool is data/zenodo_no_gt_cached/jabs_grooming/ (the download without session 2010,
features cached), made by student_scripts/prepare_training_set.py. Two ways to make the files.
Prefer the GUI, because only the GUI writes the training report.

    # A. GUI (recommended): the instructor trains in the JABS GUI on the training pool.
    python developer/scripts/make_pretrained_classifier.py --prepare-gui-project
        # Makes (or refreshes) the training pool. Open that folder as a project in the JABS GUI,
        # set the Cross Validation grouping and k (all-k is a good choice), and click Train.
    python developer/scripts/make_pretrained_classifier.py --collect-gui-results
        # Copies the saved classifier and the newest training report into data/pretrained/.

    # B. Command line only (no training report): trains with jabs-classify.
    python developer/scripts/make_pretrained_classifier.py

Session 2010 must never be in the project the classifier is trained on, or the notebook's
evaluation on it is no longer a held-out test. Every mode checks for it.

The pickle is tied to the pinned xgboost and scikit-learn versions in requirements.txt;
rebuild it when those change.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO / "student_scripts"))
from prepare_training_set import HELD_OUT, POSE_SUFFIX, TRAINING_SET, jabs_exe, prepare  # noqa: E402

OUT_DIR = REPO / "data" / "pretrained"
OUTPUT = OUT_DIR / "grooming_zenodo_full.pickle"
OUTPUT_REPORT = OUT_DIR / "grooming_zenodo_full_training_report.md"
BEHAVIOR = "grooming"


def run(cmd: list[str]) -> None:
    """Run a JABS command, echoing its last output lines; exit if it fails.

    Args:
        cmd: Command and arguments.
    """
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}  # progress spinners need UTF-8 on Windows
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = (result.stdout or "").strip().splitlines()[-3:]
    print(f"  $ {Path(cmd[0]).stem} {' '.join(cmd[1:3])} ...")
    for line in tail:
        print(f"    {line}")
    if result.returncode != 0:
        print((result.stderr or "").strip()[-1500:])
        raise SystemExit(f"{Path(cmd[0]).stem} failed (exit {result.returncode})")


def assert_held_out_absent(project: Path) -> None:
    """Exit if any held-out session is in the project (it would leak into training).

    Args:
        project: A JABS project directory.
    """
    leaked = [s for s in HELD_OUT if (project / f"{s}{POSE_SUFFIX}").exists()
              or (project / "jabs" / "annotations" / f"{s}.json").exists()]
    if leaked:
        raise SystemExit(f"Session(s) {', '.join(sorted(leaked))} are in {project}; they must stay held out. "
                         "Re-run with --prepare-gui-project.")


def prepare_gui_project() -> None:
    """Make or refresh the training pool and say how to train in the GUI."""
    project = prepare()
    print(f"""
Ready: {project}

Next, in the JABS GUI:
  1. Open that folder as a project and select the behavior "{BEHAVIOR}".
  2. Set the Cross Validation grouping (Video) and tick All k-fold Cross Validation.
  3. Click Train, and wait for the training report to open.
Then run:  python developer/scripts/make_pretrained_classifier.py --collect-gui-results""")


def collect_gui_results() -> None:
    """Copy the GUI-trained classifier and its newest training report into data/pretrained/."""
    assert_held_out_absent(TRAINING_SET)
    classifier = TRAINING_SET / "jabs" / "classifiers" / f"{BEHAVIOR}.pickle"
    reports = sorted((TRAINING_SET / "jabs" / "training_logs").glob(f"{BEHAVIOR}_*_training_report.md"))
    if not classifier.exists() or not reports:
        raise SystemExit(f"Nothing to collect in {TRAINING_SET / 'jabs'}: click Train in the GUI first "
                         f"(needs classifiers/{classifier.name} and a training report).")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(classifier, OUTPUT)
    shutil.copy2(reports[-1], OUTPUT_REPORT)
    print(f"Copied {classifier.name} -> {OUTPUT}\nCopied {reports[-1].name} -> {OUTPUT_REPORT}")
    print("Commit both files in data/pretrained/ with the repo.")


def train_with_cli() -> None:
    """Train with jabs-classify (no training report) and write data/pretrained/grooming_zenodo_full.pickle."""
    project = prepare()
    assert_held_out_absent(project)
    with tempfile.TemporaryDirectory(prefix="jabs_pretrain_") as tmp:
        training = Path(tmp) / f"{BEHAVIOR}_training.h5"
        print("Exporting training data ...")
        run([jabs_exe("jabs-cli"), "export-training", "--behavior", BEHAVIOR, "--classifier", "xgboost",
             "--outfile", str(training), str(project)])

        print("Training ...")
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        run([jabs_exe("jabs-classify"), "train", str(training), str(OUTPUT)])
    print(f"\nWrote {OUTPUT} ({OUTPUT.stat().st_size / 1e3:.0f} KB). No training report: use the GUI route for one.")


def main() -> None:
    """Dispatch on the command-line flag; see the module docstring for the workflow."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--prepare-gui-project", action="store_true",
                      help="make or refresh the training pool to train in the JABS GUI")
    mode.add_argument("--collect-gui-results", action="store_true",
                      help="copy the GUI-trained classifier and training report into data/pretrained/")
    args = parser.parse_args()
    if args.prepare_gui_project:
        prepare_gui_project()
    elif args.collect_gui_results:
        collect_gui_results()
    else:
        train_with_cli()


if __name__ == "__main__":
    main()
