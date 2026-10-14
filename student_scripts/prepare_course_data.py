"""Get the course data ready in one call: download, training pool, practice set, cached features.

Called by the one-click launchers (start_jabs.ps1 / start_jabs.sh); safe to run by hand and to
re-run. It does, in order:

    1. Downloads and extracts the Zenodo grooming dataset into data/zenodo/ if it is not there
       (download_zenodo.py). If the data was copied onto the machine as the instructors' training
       pool (data/zenodo_no_gt_cached/) instead, that is used and nothing is downloaded.
    2. Builds the practice set, data/zenodo_scrubbed/, if it is missing or still holds session
       2010 (make_scrubbed_practice_set.py). An existing practice set is never rebuilt, because
       a rebuild would overwrite the labels a student has made in the GUI.
    3. Initializes the practice set with jabs-init and caches its 10 sessions' features the way
       the GUI asks for them, so the first Train does not stall. Once cached, later runs skip it.

The training pool (data/zenodo_no_gt_cached/, all 24 sessions) is for instructors who rebuild the
fallback classifier; students never need it, so this script does not touch it.

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
from prepare_training_set import HELD_OUT, SOURCE, TRAINING_SET, cache_features

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
                             "--files", "jabs_grooming.zip", "--extract"], check=False)
    return result.returncode == 0 and have_pose(SOURCE)


def main() -> int:
    """Run the steps above.

    Returns:
        0 if the practice set is ready, 1 if the download or a build step failed.
    """
    if not have_pose(SOURCE) and not have_pose(TRAINING_SET) and not download():
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
            print("[INFO] Checking cached features for the practice set ...", flush=True)
            cache_features(PRACTICE_SET)   # returns at once when they are all cached
    except (SystemExit, Exception) as err:  # noqa: BLE001 - a build problem must not stop the launcher
        print(f"[WARN] Practice-set build failed ({err}).")
        return 1
    print("[OK] Course data ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
