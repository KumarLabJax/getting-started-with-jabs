"""Build a half-labelled practice set for live JABS GUI annotation.

Run automatically by start_jabs.ps1 / start_jabs.sh on first launch, or by hand
(see Usage). Pulls every session's pose + video from the extracted Zenodo
project into data/zenodo_scrubbed/<set>/. About half of the videos
(KEEP_LABELS_FRACTION of the sessions) keep their original Zenodo annotation,
with every behavior and not-behavior bout intact; the rest have their
annotation withheld, so they open in the JABS GUI with no labels, ready for
hands-on annotation.

The practice set is also a SUBSET of the Zenodo deposit: only the PRACTICE_SESSION_COUNT
shortest videos (by frame count, ties broken by session id) are kept, so that feature
extraction, training and classification stay fast in a live session. The videos that
were left out are listed in the generated README.md.

Which sessions keep their labels is deterministic: sessions that have at least
one labelled bout are ranked by sha256(SPLIT_SALT + session), and the first
round(KEEP_LABELS_FRACTION * <number of sessions>) are kept. There is no RNG
state, so every build, on every machine, scrubs the same way. Some Zenodo
sessions have no annotation at all and are always unlabelled, so the ranked
pool is limited to sessions that have labels.

The one exception runs the other way: EXCLUDE_SESSIONS lists sessions that are
left out of the practice project entirely. Today that's just the notebook's
dense, fully-reviewed ground-truth session (2010), which lives in
data/dense_gt_a1/ and is the held-out test set the notebook evaluates against.
Keeping it out of the project means nothing labeled in the GUI (and nothing
exported for training) can ever include it.

Features are computed at build time: after the files are copied, `jabs-init`
caches every session's features in the project, so the GUI opens with features
ready and the first Train click does not stall a live session. Feature caches
of sessions that are not in the set (including the held-out one) are deleted.

This script only ever reads from the Zenodo source and writes to a separate
output directory - the training pool (data/zenodo_no_gt_cached/jabs_grooming/, made by prepare_training_set.py from the
download in data/zenodo/) is never
modified, so it stays available as an untouched copy of the original,
publicly-annotated deposit (useful on its own, e.g. for inter-rater
reliability comparisons between Zenodo's original annotations and whatever
students produce during hands-on practice).

Draws from:
    jabs_grooming (data/zenodo_no_gt_cached/jabs_grooming/) - the only Zenodo set with
    video, so the only one usable for hands-on GUI annotation
    (jabs_single_mouse_behaviors ships pose+annotations only, no video, and
    isn't included here).

Usage:
    # 1. Download and extract first (see student_scripts/download_zenodo.py):
    python student_scripts/download_zenodo.py --files jabs_grooming.zip --extract

    # 2. Build the scrubbed set:
    python student_scripts/make_scrubbed_practice_set.py

Output goes to data/zenodo_scrubbed/ (gitignored). Nothing is uploaded anywhere.
"""

import hashlib
import json
import shutil
from pathlib import Path

import h5py
from prepare_training_set import TRAINING_SET, cache_features, prepare

REPO = Path(__file__).parent.parent
DEFAULT_OUTPUT = REPO / "data" / "zenodo_scrubbed"
POSE_SUFFIX = "_pose_est_v6.h5"
VIDEO_SUFFIX = ".avi"

# The Zenodo set this pulls from - see module docstring for why
# jabs_single_mouse_behaviors (no video) isn't included.
DEFAULT_SOURCES = {
    "jabs_grooming": TRAINING_SET,
}

# How many videos the practice set keeps. The deposit has 25 videos; the shortest
# ones are kept so a full pass (features, training, classifying every session)
# fits in a live session. The held-out session (EXCLUDE_SESSIONS) never counts.
PRACTICE_SESSION_COUNT = 10

# Fraction of the practice sessions that keep their original labels, and the
# fixed salt that makes the choice of which ones deterministic. Changing either
# changes which sessions are labelled, so treat both as part of the course.
KEEP_LABELS_FRACTION = 0.5
SPLIT_SALT = "jabs-getting-started-v3"

# Pose-quality (QC) criteria that produce qc_passed_sessions.json. The live
# notebook does not teach QC; it points to the Precomputed Tracking & QC page and
# hands out the sessions that already passed. These are the same thresholds that
# page uses.
QC_LOW_CONF_THRESHOLD = 0.3  # a frame is "low confidence" if its mean keypoint confidence is below this
QC_MAX_LOW_CONF_PCT = 0.20  # fail a session if more than 20% of its frames are low confidence
QC_MIN_FRAMES = 500  # fail a session shorter than this (likely truncated)

# Sessions left out of the practice project entirely (held out as the test set).
EXCLUDE_SESSIONS = {
    "jabs_grooming": {"2010"},
}


def discover_sessions(source: Path) -> list[str]:
    """Return every session stem with a pose file in an extracted Zenodo project.

    Args:
        source: Directory of an extracted Zenodo project.

    Returns:
        Sorted session stems, i.e. the names of files matching `*POSE_SUFFIX`
        with the suffix removed.
    """
    return sorted(p.name[: -len(POSE_SUFFIX)] for p in source.glob(f"*{POSE_SUFFIX}"))


def has_labels(annotation: Path) -> bool:
    """Return whether an annotation file contains at least one labelled bout.

    Args:
        annotation: Path to a JABS annotation JSON (`jabs/annotations/<stem>.json`).

    Returns:
        True if the file exists and any identity has at least one labelled
        segment (behavior or not-behavior) for any behavior.
    """
    if not annotation.exists():
        return False
    labels = json.loads(annotation.read_text(encoding="utf-8")).get("labels", {})
    return any(bouts for behaviors in labels.values() for bouts in behaviors.values())


def session_size(source: Path, stem: str) -> tuple[int, float]:
    """Measure one session: its length in frames and its video size.

    Args:
        source: Directory of an extracted Zenodo project.
        stem: Session stem.

    Returns:
        (number of frames in the pose file, video file size in MB; 0.0 if there is no video).
    """
    with h5py.File(source / f"{stem}{POSE_SUFFIX}", "r") as f:
        frames = int(f["poseest/points"].shape[0])
    video = source / f"{stem}{VIDEO_SUFFIX}"
    return frames, (video.stat().st_size / 1e6 if video.exists() else 0.0)


def select_shortest_sessions(source: Path, sessions: list[str], count: int) -> list[str]:
    """Choose the shortest videos for the practice set.

    Args:
        source: Directory of an extracted Zenodo project.
        sessions: Candidate session stems (after exclusions).
        count: How many to keep.

    Returns:
        The kept stems, sorted. Sessions are ranked by frame count, then by stem, so the
        choice is identical on every run.
    """
    ranked = sorted(sessions, key=lambda s: (session_size(source, s)[0], s))
    return sorted(ranked[:count])


def select_labelled_sessions(sessions: list[str], has_label: set[str]) -> set[str]:
    """Deterministically choose which sessions keep their original labels.

    Sessions in `has_label` are ranked by sha256(SPLIT_SALT + session) and the
    first round(KEEP_LABELS_FRACTION * len(sessions)) are kept (capped at the
    number of sessions that have labels). The ranking depends only on the
    session names, so it is identical on every run and machine.

    Args:
        sessions: All practice sessions (after exclusions).
        has_label: The subset of `sessions` that have at least one labelled bout.

    Returns:
        The set of session stems that keep their labels.
    """
    target = round(KEEP_LABELS_FRACTION * len(sessions))
    ranked = sorted(
        has_label,
        key=lambda s: hashlib.sha256((SPLIT_SALT + s).encode("utf-8")).hexdigest(),
    )
    return set(ranked[:target])


def write_qc_passed_sessions(set_output: Path, sessions: list[str]) -> list[str]:
    """Write qc_passed_sessions.json for the practice sessions.

    A session passes if no more than QC_MAX_LOW_CONF_PCT of its frames have a
    mean keypoint confidence below QC_LOW_CONF_THRESHOLD, and it has at least
    QC_MIN_FRAMES frames. The file records the thresholds it used.

    Args:
        set_output: Output directory of the set holding the copied pose files.
        sessions: Session stems to assess.

    Returns:
        The stems that passed QC, in the order given.
    """
    passed = []
    for stem in sessions:
        with h5py.File(set_output / f"{stem}{POSE_SUFFIX}", "r") as f:
            conf = f["poseest/confidence"][:, 0, :]  # (n_frames, n_keypoints)
        pct_low_conf = float((conf.mean(axis=1) < QC_LOW_CONF_THRESHOLD).mean())
        if pct_low_conf <= QC_MAX_LOW_CONF_PCT and conf.shape[0] >= QC_MIN_FRAMES:
            passed.append(stem)
    qc = {
        "qc_parameters": {
            "low_conf_threshold": QC_LOW_CONF_THRESHOLD,
            "max_low_conf_pct": QC_MAX_LOW_CONF_PCT,
            "min_frames": QC_MIN_FRAMES,
        },
        "passed_sessions": [{"file": f"{s}{POSE_SUFFIX}", "subject_id": s} for s in passed],
    }
    (set_output / "qc_passed_sessions.json").write_text(json.dumps(qc, indent=2), encoding="utf-8")
    return passed


def prune_stale_features(set_output: Path, keep: list[str]) -> None:
    """Delete cached features for sessions that are not in the practice set.

    An older build, or an older notebook run, may have left features for
    sessions that are no longer here (including the held-out session). Features
    live in jabs/features/<session>/ and jabs/cache/<session>_pose_est_v6_cache.h5.

    Args:
        set_output: Output directory of the set.
        keep: Session stems that stay in the practice set.
    """
    features = set_output / "jabs" / "features"
    if features.is_dir():
        for d in features.iterdir():
            if d.is_dir() and d.name not in keep:
                shutil.rmtree(d)
    cache = set_output / "jabs" / "cache"
    if cache.is_dir():
        for f in cache.glob(f"*{POSE_SUFFIX.removesuffix('.h5')}_cache.h5"):
            if f.name.removesuffix(f"{POSE_SUFFIX.removesuffix('.h5')}_cache.h5") not in keep:
                f.unlink()


def make_scrubbed_set(sources: dict, output: Path) -> None:
    """Build the half-labelled practice set for each source project.

    For each set, copies the PRACTICE_SESSION_COUNT shortest sessions' pose files
    (and videos, if present) into output/<set_name>/; every other video is left
    out and listed in the README, and stale copies of them from an older build
    are deleted. Sessions chosen by select_labelled_sessions also
    get their original annotation JSON copied unchanged; every other session
    is deliberately left without one, and any stale annotation left by an
    older build is deleted so rebuilds are idempotent.
    Sessions listed in EXCLUDE_SESSIONS for that set are skipped, and any
    stale copy of an excluded session (pose, video, or annotation) left in
    the output by an older build is deleted so it cannot leak into training.
    A pruned jabs/project.json (video_files limited to the copied sessions)
    is written when the source has one, then jabs-init caches every session's
    features (stale caches of sessions no longer in the set are deleted first),
    plus a README.md. Sets with no
    sessions to copy are skipped. Prints progress and a final total.

    Args:
        sources: Mapping of set name to the extracted source project directory.
        output: Root output directory; one subdirectory is created per set.
    """
    total = 0
    for set_name, source in sources.items():
        excluded = EXCLUDE_SESSIONS.get(set_name, set())
        all_sessions = discover_sessions(source)
        candidates = [s for s in all_sessions if s not in excluded]
        sessions = select_shortest_sessions(source, candidates, PRACTICE_SESSION_COUNT)
        removed = [s for s in candidates if s not in sessions]
        if not sessions:
            print(f"  {set_name}: no sessions found in {source} - skipping")
            continue

        set_output = output / set_name
        (set_output / "jabs").mkdir(parents=True, exist_ok=True)

        ann_src = source / "jabs" / "annotations"
        labelled = select_labelled_sessions(
            sessions, {s for s in sessions if has_labels(ann_src / f"{s}.json")}
        )
        (set_output / "jabs" / "annotations").mkdir(parents=True, exist_ok=True)

        scrubbed = []
        for stem in sessions:
            pose_src = source / f"{stem}{POSE_SUFFIX}"
            shutil.copy2(pose_src, set_output / pose_src.name)

            vid_src = source / f"{stem}{VIDEO_SUFFIX}"
            vid_note = ""
            if vid_src.exists():
                shutil.copy2(vid_src, set_output / vid_src.name)
                vid_note = " + video"
            ann_dst = set_output / "jabs" / "annotations" / f"{stem}.json"
            if stem in labelled:
                shutil.copy2(ann_src / f"{stem}.json", ann_dst)
                ann_note = "original labels kept"
            else:
                ann_dst.unlink(missing_ok=True)
                ann_note = "no annotations"
            scrubbed.append(stem)
            print(f"    {stem} (pose{vid_note}, {ann_note})")
        for stem in removed:
            # Videos left out of the practice set: remove any copy an older build left behind.
            for stale in (
                set_output / f"{stem}{POSE_SUFFIX}",
                set_output / f"{stem}{VIDEO_SUFFIX}",
                set_output / "jabs" / "annotations" / f"{stem}.json",
            ):
                stale.unlink(missing_ok=True)
        print(f"    removed from the practice set (not among the {PRACTICE_SESSION_COUNT} shortest): {', '.join(removed)}")
        for stem in sorted(excluded):
            # An older build of this set may still hold the excluded session
            # (pose, video, injected annotation); remove it so it cannot leak.
            for stale in (
                set_output / f"{stem}{POSE_SUFFIX}",
                set_output / f"{stem}{VIDEO_SUFFIX}",
                set_output / "jabs" / "annotations" / f"{stem}.json",
            ):
                stale.unlink(missing_ok=True)
            print(f"    excluded {stem} (held out; see data/dense_gt_a1/)")

        # Prune jabs/project.json to just this set's sessions, same technique as
        # the toy-sample builder.
        src_proj = source / "jabs" / "project.json"
        if src_proj.exists():
            proj = json.loads(src_proj.read_text(encoding="utf-8"))
            wanted = {f"{stem}{VIDEO_SUFFIX}" for stem in scrubbed}
            proj["video_files"] = {
                k: v for k, v in proj.get("video_files", {}).items() if k in wanted
            }
            (set_output / "jabs" / "project.json").write_text(
                json.dumps(proj, indent=2), encoding="utf-8"
            )

        prune_stale_features(set_output, scrubbed)
        print(f"  {set_name}: computing features with jabs-init ...")
        if cache_features(set_output):
            print(f"  {set_name}: features cached for {len(scrubbed)} sessions")

        qc_passed = write_qc_passed_sessions(set_output, scrubbed)
        print(f"  {set_name}: {len(qc_passed)} of {len(scrubbed)} sessions passed pose QC")

        removed_info = [(stem, *session_size(source, stem)) for stem in removed]
        write_readme(set_output, set_name, scrubbed, sorted(excluded), sorted(labelled), removed_info, len(all_sessions))
        total += len(scrubbed)
        print(f"  {set_name}: {len(labelled)} labelled, {len(scrubbed) - len(labelled)} unlabelled")

    print(f"\nDone: {total} session(s) written into {output}")


def write_readme(
    set_output: Path,
    set_name: str,
    scrubbed: list[str],
    excluded: list[str],
    labelled: list[str],
    removed: list[tuple[str, int, float]],
    n_total: int,
) -> None:
    """Write README.md in a scrubbed set directory describing its contents.

    The README gives attribution and the CC BY-NC-4.0 licensing note, lists
    the practice sessions split into labelled and unlabelled, and lists the
    held-out (excluded) sessions. Overwrites any existing README.md.

    Args:
        set_output: Output directory of the set; README.md is written here.
        set_name: Name of the Zenodo set the data came from.
        scrubbed: Session stems included in the practice set.
        excluded: Session stems held out of the practice set.
        labelled: Subset of `scrubbed` that keep their original annotations.
        removed: (session, frames, video MB) for each video left out of the practice set.
        n_total: Number of videos in the full Zenodo set this was built from.
    """
    try:
        heading_path = set_output.relative_to(REPO)
    except ValueError:
        heading_path = set_output
    unlabelled = [s for s in scrubbed if s not in set(labelled)]
    labelled_block = chr(10).join(f"- {s}" for s in labelled) if labelled else "(none)"
    unlabelled_block = chr(10).join(f"- {s}" for s in unlabelled) if unlabelled else "(none)"
    excluded_block = chr(10).join(f"- {s}" for s in excluded) if excluded else "(none)"
    removed_rows = chr(10).join(
        f"| {stem} | {frames:,} | {mb:.1f} |" for stem, frames, mb in sorted(removed, key=lambda r: (r[1], r[0]))
    )
    text = f"""\
# {heading_path}/

Derived from the Zenodo "JABS Behavior Classifier Example Projects" deposit
(Geuther, Brian. "JABS Behavior Classifier Example Projects." Zenodo, 2024.
https://doi.org/10.5281/zenodo.16697331. License: CC BY-NC-4.0), set `{set_name}`.

## What this is

Pose + video for every practice session. About half keep their original
behavior annotations (all behavior and not-behavior bouts); the rest have
them withheld so they open in the JABS GUI with no labels, for hands-on
annotation practice. Which sessions keep their labels is deterministic
(see `SPLIT_SALT` in the script), so every build is identical.

### With original labels

{labelled_block}

### Labels withheld (annotate these yourself)

{unlabelled_block}

## Removed from the full Zenodo set

The Zenodo deposit has {n_total} videos. To keep a full pass (features, training,
classifying every session) fast in a live session, this practice set keeps only the
{len(scrubbed)} shortest videos (by frame count; session 2010 is held out below and
never counted). These {len(removed)} videos were removed from the practice set; they are
still in the full download at `data/zenodo/{set_name}/` (and in `data/zenodo_no_gt_cached/{set_name}/`):

| Session | Frames | Video (MB) |
|---------|-------:|-----------:|
{removed_rows}

## Held out

These sessions are left out of the project on purpose. They are fully
reviewed ground-truth sessions kept in `data/dense_gt_a1/` and used only to test
a trained classifier, so they must never be part of training:

{excluded_block}

`qc_passed_sessions.json` lists the sessions whose pose passed quality
control (the thresholds are recorded in the file); the live walkthrough
classifies sessions from that list.

Generated by `student_scripts/make_scrubbed_practice_set.py` (see
`EXCLUDE_SESSIONS` in that script) - regenerate to reproduce this exact set.
The source this was built from (`data/zenodo_no_gt_cached/{set_name}/`, itself made from `data/zenodo/{set_name}/`) is
untouched and still has every session's real, original Zenodo annotation
intact.

## Licensing

This is a derived subset of a CC BY-NC-4.0 dataset. The license requires
attribution (above) and non-commercial use. Do not redistribute it commercially.
"""
    (set_output / "README.md").write_text(text, encoding="utf-8")


def main() -> None:
    """Prepare the training pool, then build the scrubbed practice set into data/zenodo_scrubbed/."""
    prepare()  # data/zenodo_no_gt_cached/: the download without session 2010, features cached
    make_scrubbed_set(DEFAULT_SOURCES, DEFAULT_OUTPUT)


if __name__ == "__main__":
    main()
