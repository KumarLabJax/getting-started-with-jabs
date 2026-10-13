"""Get the course data ready in one call: download, training pool, practice set, cached features.

Called by the one-click launchers (start_jabs.ps1 / start_jabs.sh); safe to run by hand and to
re-run. It does, in order:

    1. Downloads and extracts the Zenodo grooming dataset into data/zenodo/ if it is not there
       (download_zenodo.py).
    2. Prepares the training pool, data/zenodo_no_gt_cached/: the download without the held-out
       session 2010, with features cached by jabs-init (prepare_training_set.py).
    3. Builds the practice set, data/zenodo_scrubbed/, if it is missing or still holds session
       2010 (make_scrubbed_practice_set.py). An existing practice set is never rebuilt, because
       a rebuild would overwrite the labels a student has made in the GUI.
    4. Runs jabs-init on the practice set, so every session's features are cached before the
       JABS GUI opens. Features already cached are skipped, so this is quick on later runs.

Usage:
    python student_scripts/prepare_course_data.py

Exit status: 0 when the practice set is ready, 1 otherwise (the launchers then carry on with the
bundled toy data).
"""

import subprocess
import sys
from pathlib import Path

from make_scrubbed_practice_set import DEFAULT_OUTPUT, POSE_SUFFIX
from make_scrubbed_practice_set import main as build_practice_set
from prepare_training_set import HELD_OUT, SOURCE, cache_features, prepare

HERE = Path(__file__).parent
PRACTICE_SET = DEFAULT_OUTPUT / "jabs_grooming"


def have_pose(folder: Path) -> bool:
    """True if the folder holds at least one pose file.

    Args:
        folder: Directory to look in.
    """
    return any(folder.glob(f"*{POSE_SUFFIX}"))


def download() -> bool:
    """Download and extract the Zenodo grooming dataset.

    Returns:
        True if the pose files are there afterwards.
    """
    print("[INFO] Downloading the Zenodo grooming dataset (~110 MB) ...")
    result = subprocess.run([sys.executable, str(HERE / "download_zenodo.py"),
                             "--files", "jabs_grooming.zip", "--extract"])
    return result.returncode == 0 and have_pose(SOURCE)


def main() -> int:
    """Run the four steps above.

    Returns:
        0 if the practice set is ready, 1 if the download or a build step failed.
    """
    if not have_pose(SOURCE) and not download():
        print("[WARN] Data download failed. Continuing with the bundled toy data; rerun to retry.")
        return 1

    # A practice set built before session 2010 was held out still contains it; rebuild so it
    # cannot leak into training. Otherwise leave an existing practice set (and its labels) alone.
    stale = any((PRACTICE_SET / f"{stem}{POSE_SUFFIX}").exists() for stem in HELD_OUT)
    try:
        if not have_pose(PRACTICE_SET) or stale:
            print("[INFO] Building the practice set (this also caches features) ...")
            build_practice_set()
        else:
            prepare()                      # training pool: keeps what is there, caches missing features
            print("[INFO] Caching features for the practice set ...")
            cache_features(PRACTICE_SET)   # jabs-init skips features that already exist
    except (SystemExit, Exception) as err:  # a build problem must not stop the launcher
        print(f"[WARN] Practice-set build failed ({err}).")
        return 1
    print("[OK] Course data ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
