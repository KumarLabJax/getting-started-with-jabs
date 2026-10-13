"""Assemble a JABS project directory from pose+video pairs and initialize it.

The project is initialized with jabs-init, ready to open in the JABS GUI.

A JABS project is just a directory of video files and their matching pose
files. `jabs-init` then computes features for the project so the GUI does not
have to during annotation.

Usage:
    python student_scripts/prepare_jabs_project.py \
        --source-dir data/prep_toy \
        --project-dir data/jabs_project \
        [--qc-list data/zenodo_scrubbed/jabs_grooming/qc_passed_sessions.json] \
        [--window 5] [--copy] [--skip-features]

By default the script symlinks the video/pose files into the project dir
(falling back to a copy if symlinks are not permitted, e.g. on Windows without
developer mode). Pass --copy to force copying.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_SOURCE_DIR = Path(__file__).parent.parent / "data" / "prep_toy"
DEFAULT_PROJECT_DIR = Path(__file__).parent.parent / "data" / "jabs_project"

POSE_SUFFIX = "_pose_est_v6.h5"


def _jabs_init_exe() -> str:
    """Resolve the jabs-init console script next to the interpreter, else PATH.

    Returns:
        The full path to jabs-init (or jabs-init.exe) beside the running
        interpreter if it exists, otherwise the bare name "jabs-init" for
        lookup on PATH.
    """
    exe_dir = Path(sys.executable).parent
    for candidate in (exe_dir / "jabs-init", exe_dir / "jabs-init.exe"):
        if candidate.exists():
            return str(candidate)
    return "jabs-init"


def find_pairs(source_dir: Path, allowed: set | None = None) -> list[tuple[Path, Path]]:
    """Return [(video, pose)] for each pose file that has a matching .mp4 video.

    Args:
        source_dir: Directory holding pose .h5 and .mp4 files.
        allowed: If given, only include pose files whose name is in this set.

    Pose files with no matching video are skipped with a printed warning.

    Returns:
        List of (video_path, pose_path) pairs.
    """
    pairs = []
    for pose in sorted(source_dir.glob(f"*{POSE_SUFFIX}")):
        if allowed is not None and pose.name not in allowed:
            continue
        video = pose.with_name(pose.name.replace(POSE_SUFFIX, ".mp4"))
        if video.exists():
            pairs.append((video, pose))
        else:
            print(f"  WARNING: no matching video for {pose.name}; skipping")
    return pairs


def _link_or_copy(src: Path, dst: Path, copy: bool) -> None:
    """Place src at dst as a symlink, falling back to a copy.

    Does nothing if dst already exists. If copy is False, tries to create a
    symlink first and falls back to a copy when symlinks are not permitted.

    Args:
        src: Existing file to link or copy.
        dst: Destination path to create.
        copy: If True, always copy instead of symlinking.
    """
    if dst.exists():
        return
    if not copy:
        try:
            os.symlink(src, dst)
            return
        except (OSError, NotImplementedError):
            pass  # fall back to copy
    shutil.copy2(src, dst)


def prepare_project(
    source_dir: Path,
    project_dir: Path,
    qc_list: Path | None = None,
    window: int = 5,
    copy: bool = False,
    skip_features: bool = False,
) -> None:
    """Assemble a JABS project from pose+video pairs and run jabs-init.

    Finds pose+video pairs in source_dir (optionally restricted by a QC list),
    links or copies them into project_dir (created if needed), then runs the
    jabs-init subprocess on project_dir. Prints progress along the way.

    Args:
        source_dir: Directory with pose .h5 and .mp4 files.
        project_dir: Output JABS project directory.
        qc_list: Optional JSON file with a `passed_sessions` list of entries
            having a `file` key; only pose files named there are used.
        window: Feature window size passed to jabs-init via -w.
        copy: If True, copy files instead of symlinking.
        skip_features: If True, pass --skip-feature-generation so the project
            is initialized but features are not computed.

    Raises:
        SystemExit: With status 1 if no pose+video pairs are found, or with
            jabs-init's return code if it exits non-zero.
    """
    allowed = None
    if qc_list is not None:
        qc = json.loads(Path(qc_list).read_text(encoding="utf-8"))
        allowed = {s["file"] for s in qc.get("passed_sessions", [])}
        print(f"QC list: {len(allowed)} passed session(s)")

    pairs = find_pairs(source_dir, allowed)
    if not pairs:
        print(f"No pose+video pairs found in {source_dir} (need *{POSE_SUFFIX} + .mp4).")
        sys.exit(1)

    print(f"Assembling {len(pairs)} session(s) into {project_dir}")
    project_dir.mkdir(parents=True, exist_ok=True)
    for video, pose in pairs:
        _link_or_copy(video, project_dir / video.name, copy)
        _link_or_copy(pose, project_dir / pose.name, copy)

    cmd = [_jabs_init_exe(), str(project_dir), "-w", str(window)]
    if skip_features:
        cmd.append("--skip-feature-generation")
    print(f"\nRunning: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        print("jabs-init failed - see output above.")
        sys.exit(result.returncode)

    print(f"\nJABS project ready at: {project_dir}")
    print("Open this directory in the JABS GUI to begin annotation.")


def main() -> None:
    """Parse command-line arguments and prepare the JABS project."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=DEFAULT_SOURCE_DIR,
        help=f"Directory with *{POSE_SUFFIX} + .mp4 pairs (default: data/prep_toy/)",
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=DEFAULT_PROJECT_DIR,
        help="JABS project output directory (default: data/jabs_project/)",
    )
    parser.add_argument(
        "--qc-list",
        type=Path,
        default=None,
        help="Optional qc_passed_sessions.json; restrict to those sessions",
    )
    parser.add_argument(
        "--window", type=int, default=5, help="jabs-init feature window size (default: 5)"
    )
    parser.add_argument(
        "--copy", action="store_true", help="Copy files instead of symlinking"
    )
    parser.add_argument(
        "--skip-features",
        action="store_true",
        help="Initialize/validate the project but skip feature computation",
    )
    args = parser.parse_args()
    prepare_project(
        args.source_dir,
        args.project_dir,
        qc_list=args.qc_list,
        window=args.window,
        copy=args.copy,
        skip_features=args.skip_features,
    )


if __name__ == "__main__":
    main()
