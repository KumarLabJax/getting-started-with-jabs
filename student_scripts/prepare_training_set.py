"""Prepare the training pool: the full Zenodo grooming set without the held-out session, features cached.

`download_zenodo.py` extracts the deposit to data/zenodo/jabs_grooming/ and leaves it as downloaded.
This script makes data/zenodo_no_gt_cached/jabs_grooming/ from it:

    - the held-out dense ground-truth session (2010) is left out: its video, pose file and annotation
      are not copied, so nothing trained or built from this folder can ever include it. (It is the
      notebook's test set and lives on its own in data/dense_gt_a1/.)
    - the project is configured for the course (grooming, window size 60, balanced labels,
      cross-validation grouped by video), `jabs-init` initializes it, and every session's features are
      cached the way the JABS GUI asks for them when you Train and Classify (see cache_features), so
      the first Train does not stall on feature extraction.

The practice-set builder (make_scrubbed_practice_set.py) and the pretrained-classifier script
(developer/scripts/make_pretrained_classifier.py) read from this folder. It is not committed, and
the download in data/zenodo/ is never modified. Training in the JABS GUI on this folder writes the
classifier and training report inside it (jabs/classifiers/, jabs/training_logs/); they are kept.

Usage (the launchers and make_scrubbed_practice_set.py call this for you):
    python student_scripts/download_zenodo.py --files jabs_grooming.zip --extract
    python student_scripts/prepare_training_set.py
"""

import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

REPO = Path(__file__).parent.parent
SOURCE = REPO / "data" / "zenodo" / "jabs_grooming"
TRAINING_SET = REPO / "data" / "zenodo_no_gt_cached" / "jabs_grooming"
HELD_OUT = {"2010"}  # the dense ground-truth session the notebook evaluates on
POSE_SUFFIX = "_pose_est_v6.h5"
BEHAVIOR = "grooming"
WINDOW_SIZE = 60  # frames before and after the current frame
CV_GROUPING = "Video"  # JABS "Cross Validation grouping": hold out whole videos
# JABS-generated folders that are not copied from the download (they are rebuilt here).
NOT_COPIED = ("features", "cache", "classifiers", "predictions", "training_logs", "archive", "session")


def jabs_exe(name: str) -> str:
    """Find a JABS console script beside this Python, else fall back to PATH.

    Args:
        name: Console script name, for example "jabs-init".

    Returns:
        The full path if the script sits beside the interpreter, otherwise the bare name.
    """
    exe_dir = Path(sys.executable).parent
    for candidate in (exe_dir / name, exe_dir / f"{name}.exe", exe_dir / "Scripts" / f"{name}.exe"):
        if candidate.exists():
            return str(candidate)
    return name


def remove_held_out(project: Path) -> None:
    """Delete every trace of the held-out sessions from a project, including cached features.

    Args:
        project: A JABS project directory.
    """
    for stem in HELD_OUT:
        for stale in (project / f"{stem}{POSE_SUFFIX}", project / f"{stem}.avi",
                      project / "jabs" / "annotations" / f"{stem}.json",
                      project / "jabs" / "cache" / f"{stem}{POSE_SUFFIX.removesuffix('.h5')}_cache.h5"):
            stale.unlink(missing_ok=True)
        shutil.rmtree(project / "jabs" / "features" / stem, ignore_errors=True)


def configure_project(project: Path) -> None:
    """Set the course's JABS project settings in jabs/project.json.

    Grooming gets window size 60 and balanced training labels, and cross-validation is grouped by
    video. The classifier type (XGBoost) and the number of folds (all k) are choices in the GUI's
    controls, not project settings, so students pick them there (see the cheatsheet).

    Args:
        project: A JABS project directory.
    """
    path = project / "jabs" / "project.json"
    proj = json.loads(path.read_text(encoding="utf-8"))
    grooming = proj.setdefault("behavior", {}).setdefault(BEHAVIOR, {})
    grooming["window_size"] = WINDOW_SIZE
    grooming["window"] = True
    grooming["balance_labels"] = True
    proj.setdefault("settings", {})["cv_grouping"] = CV_GROUPING
    proj["window_sizes"] = sorted({WINDOW_SIZE, *proj.get("window_sizes", [])})
    path.write_text(json.dumps(proj, indent=2), encoding="utf-8")


def init_project(project: Path) -> bool:
    """Run `jabs-init` to validate and initialize the project, without computing features.

    Features come from cache_behavior_features instead: jabs-init computes them with the project
    defaults, which are not the settings the GUI uses for grooming, so the GUI ignores them.

    Args:
        project: A JABS project directory.

    Returns:
        True if jabs-init succeeded, False if it failed or could not be started.
    """
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}  # the progress spinner needs UTF-8 on Windows
    try:
        result = subprocess.run([jabs_exe("jabs-init"), "--skip-feature-generation", "-w", str(WINDOW_SIZE),
                                 str(project)], env=env, capture_output=True, text=True,
                                encoding="utf-8", errors="replace")
    except OSError as err:
        print(f"  jabs-init could not be started ({err}).")
        return False
    if result.returncode != 0:
        print("  jabs-init failed.")
        for line in (result.stderr or result.stdout or "").strip().splitlines()[-5:]:
            print(f"    {line}")
        return False
    return True


def _cache_one_video(args: tuple[str, str]) -> str:
    """Cache one video's features with the grooming behavior's settings (runs in a worker process).

    Mirrors what the JABS GUI does on Train and Classify: IdentityFeatures built with the behavior
    settings from project.json, then the per-frame and window features read, which writes the cache.

    Args:
        args: (project directory, video stem).

    Returns:
        The video stem, once its features are cached.
    """
    project_dir, stem = Path(args[0]), args[1]
    import jabs.feature_extraction as fe
    from jabs.core.enums import CacheFormat
    from jabs.pose_estimation import open_pose_file
    from jabs.video_reader.utilities import get_fps_and_nframes

    proj = json.loads((project_dir / "jabs" / "project.json").read_text(encoding="utf-8"))
    behavior_settings = proj["behavior"][BEHAVIOR]
    cache_format = CacheFormat(proj.get("settings", {}).get("cache_format", "hdf5"))
    video = f"{stem}.avi"
    pose_est = open_pose_file(project_dir / f"{stem}{POSE_SUFFIX}", project_dir / "jabs" / "cache")
    fps, _ = get_fps_and_nframes(str(project_dir / video))
    for identity in pose_est.identities:
        features = fe.IdentityFeatures(video, identity, project_dir / "jabs" / "features", pose_est, fps=fps,
                                       op_settings=behavior_settings, cache_format=cache_format)
        features.get_features(behavior_settings.get("window_size", WINDOW_SIZE))
    return stem


def cache_behavior_features(project: Path) -> bool:
    """Cache every session's features with the settings the GUI uses for grooming.

    Args:
        project: A JABS project directory.

    Returns:
        True if every video's features were cached, False if any failed (JABS then computes
        them on first Train instead).
    """
    stems = sorted(f.name.removesuffix(POSE_SUFFIX) for f in project.glob(f"*{POSE_SUFFIX}"))
    ok = True
    with ProcessPoolExecutor(max_workers=max(1, min(len(stems), (os.cpu_count() or 2) - 1))) as pool:
        futures = {pool.submit(_cache_one_video, (str(project), stem)): stem for stem in stems}
        for future, stem in futures.items():
            try:
                future.result()
            except Exception as err:  # one bad video must not stop the others
                ok = False
                print(f"  features for {stem} failed ({err}); JABS will compute them on first Train.")
    return ok


def cache_features(project: Path) -> bool:
    """Configure the project, initialize it with `jabs-init`, and cache all features for grooming.

    Features already cached with the right settings are read, not recomputed, so this is quick on
    later runs.

    Args:
        project: A JABS project directory.

    Returns:
        True if every step succeeded. A failure is reported but not fatal: JABS computes features
        on demand.
    """
    configure_project(project)
    return init_project(project) and cache_behavior_features(project)


def prepare(source: Path = SOURCE, destination: Path = TRAINING_SET) -> Path:
    """Build or refresh the training pool and return its path.

    Copies the download if the folder does not exist yet; otherwise keeps what is there (including
    a classifier and training report made in the GUI). Either way the held-out session is removed
    and features are cached.

    Args:
        source: The extracted Zenodo grooming project.
        destination: Where the training pool goes.

    Returns:
        The destination folder.

    Raises:
        SystemExit: If the download is missing.
    """
    if not destination.exists():
        if not list(source.glob(f"*{POSE_SUFFIX}")):
            raise SystemExit(
                f"No pose files in {source}.\n"
                "Run: python student_scripts/download_zenodo.py --files jabs_grooming.zip --extract"
            )
        print(f"Copying {source} to {destination} ...")
        shutil.copytree(source, destination, ignore=shutil.ignore_patterns(*NOT_COPIED))
    remove_held_out(destination)
    print(f"Training pool: {destination} (held out: {', '.join(sorted(HELD_OUT))}); caching features ...")
    if cache_features(destination):
        print("  features cached.")
    return destination


if __name__ == "__main__":
    prepare()
