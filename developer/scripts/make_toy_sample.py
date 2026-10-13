r"""Build the committed toy sample for the course from a JABS example project.

Selects a few label-rich sessions from an extracted JABS project (pose clips +
annotations) and copies their pose files and annotation JSONs into data/toy/,
which IS committed to the repo. The notebooks (00-05) and CI run against this
small sample without needing the full project download.

Clips are copied whole (no frame slicing). The matching video (<stem>.avi) is
copied too when a full extraction provides it, so the clips can be opened in the
JABS GUI. Videos are gitignored (kept untracked): only the GUI exercise needs
them, and CI runs the notebooks headless. Sessions shorter than MIN_FRAMES are
skipped so the toy passes notebook 03's QC.

The course's canonical project is the Zenodo "jabs_grooming" example (one clean
behavior, small clips); pass --source to build from a different JABS project.

Usage:
    python student_scripts/download_zenodo.py --files jabs_grooming.zip \
        --output data --extract            # -> data/jabs_grooming/
    python developer/scripts/make_toy_sample.py [--n 3]
"""

import argparse
import json
import shutil
from pathlib import Path

REPO = Path(__file__).parent.parent.parent
DEFAULT_SOURCE = REPO / "data" / "jabs_grooming"
DEFAULT_OUTPUT = REPO / "data" / "toy"
POSE_SUFFIX = "_pose_est_v6.h5"
VIDEO_SUFFIX = ".avi"
# Bias selection so the toy set exercises NB05's behavior-vs-speed analysis.
PREFERRED_BEHAVIOR = "grooming"
# Skip clips shorter than this so the toy passes notebook 03's QC (min_frames).
MIN_FRAMES = 1000


def _positive_counts(ann_path: Path) -> tuple[int, bool, int]:
    """Count positive label intervals in one annotation JSON file.

    Args:
        ann_path: Path to a JABS annotation JSON file.

    Returns:
        A tuple of (n_positive, has_preferred, num_frames): the number of
        intervals marked present, whether any present interval belongs to
        PREFERRED_BEHAVIOR, and the clip's frame count (0 if absent).
    """
    d = json.loads(ann_path.read_text(encoding="utf-8"))
    n_pos, has_pref = 0, False
    for behaviors in d.get("labels", {}).values():
        for behavior, intervals in behaviors.items():
            pos = [iv for iv in intervals if iv.get("present")]
            n_pos += len(pos)
            if behavior == PREFERRED_BEHAVIOR and pos:
                has_pref = True
    return n_pos, has_pref, int(d.get("num_frames") or 0)


def select_sessions(source: Path, n: int) -> list[str]:
    """Pick n session stems: long enough for QC, preferred-behavior first, then most-labeled.

    Args:
        source: Extracted JABS project directory.
        n: Maximum number of sessions to return.

    Returns:
        A list of up to n session stems, ranked best first. Sessions with fewer
        than MIN_FRAMES frames are excluded.
    """
    ann_dir = source / "jabs" / "annotations"
    scored = []
    for ann in sorted(ann_dir.glob("*.json")):
        n_pos, has_pref, num_frames = _positive_counts(ann)
        if num_frames < MIN_FRAMES:
            continue  # too short to pass notebook 03's QC
        scored.append((ann.stem, n_pos, has_pref))
    # rank: preferred-behavior sessions first, then by positive-label count
    scored.sort(key=lambda s: (s[2], s[1]), reverse=True)
    return [stem for stem, _, _ in scored[:n]]


def make_toy(source: Path, output: Path, n: int) -> None:
    """Copy selected sessions from a JABS project into the toy sample directory.

    Copies each selected session's pose file and annotation JSON (plus the video
    when present in the source), then writes a project.json pruned to the copied
    sessions. Prints progress and a summary.

    Args:
        source: Extracted JABS project directory.
        output: Destination toy directory; created if missing.
        n: Number of sessions to select.

    Raises:
        SystemExit: If the source has no jabs/annotations directory.
    """
    if not (source / "jabs" / "annotations").is_dir():
        raise SystemExit(
            f"Source not found: {source}. Extract the Zenodo bundle first "
            "(download_zenodo.py --extract)."
        )
    stems = select_sessions(source, n)
    (output / "jabs" / "annotations").mkdir(parents=True, exist_ok=True)

    total_mb = 0.0
    copied = []
    for stem in stems:
        pose_src = source / f"{stem}{POSE_SUFFIX}"
        ann_src = source / "jabs" / "annotations" / f"{stem}.json"
        if not pose_src.exists() or not ann_src.exists():
            print(f"  SKIP {stem} (missing pose or annotation)")
            continue
        shutil.copy2(pose_src, output / pose_src.name)
        shutil.copy2(ann_src, output / "jabs" / "annotations" / ann_src.name)
        mb = pose_src.stat().st_size / 1e6
        total_mb += mb

        # Copy the matching video when a full extraction provides it. Videos
        # stay untracked (gitignored); they are only for the JABS GUI exercise.
        vid_src = source / f"{stem}{VIDEO_SUFFIX}"
        vid_note = ""
        if vid_src.exists():
            shutil.copy2(vid_src, output / vid_src.name)
            vid_note = f" + {vid_src.stat().st_size / 1e6:.0f} MB video"
        copied.append(stem)
        print(f"  added {stem}  ({mb:.1f} MB pose + annotation{vid_note})")

    # Write a JABS project.json pruned to the copied sessions so the toy dir
    # opens in the JABS GUI: video_files trimmed to these clips (not the full
    # project's session list), but the curated behavior config is left exactly
    # as published (any disabled behaviors stay disabled - do not re-add).
    src_proj = source / "jabs" / "project.json"
    if src_proj.exists():
        proj = json.loads(src_proj.read_text(encoding="utf-8"))
        wanted = {f"{stem}{VIDEO_SUFFIX}" for stem in copied}
        proj["video_files"] = {
            k: v for k, v in proj.get("video_files", {}).items() if k in wanted
        }
        (output / "jabs" / "project.json").write_text(
            json.dumps(proj, indent=2), encoding="utf-8"
        )
        print(f"  wrote jabs/project.json (pruned to {len(proj['video_files'])} session(s))")

    print(f"\nToy sample written to {output}: {len(copied)} session(s), ~{total_mb:.1f} MB pose.")
    print("Notebooks 01/02/03/05 read the pose+labels; NB00 verifies them.")
    print("Videos (.avi), if present in the source, are copied for JABS but stay untracked.")


def main() -> None:
    """Parse command-line arguments and build the toy sample."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE,
                        help="Extracted JABS project dir (default: data/jabs_grooming/)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="Toy output dir (default: data/toy/)")
    parser.add_argument("--n", type=int, default=3, help="Number of sessions to include (default: 3)")
    args = parser.parse_args()
    make_toy(args.source, args.output, args.n)


if __name__ == "__main__":
    main()
