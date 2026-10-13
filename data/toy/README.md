# data/toy/

A small, self-contained slice of the course's canonical dataset: the JABS
"single mouse behaviors" example project published on Zenodo. It is committed
to the repo so the notebooks and CI can run end-to-end without the
full ~2.8 GB download.

Each session here is a 9000-frame (5 min @ 30 fps) clip with its pose, its
hand-labeled behavior annotations, and (locally) its video.

## Contents

| Path | Tracked? | Contents |
|------|----------|----------|
| `*_pose_est_v6.h5` (3 files) | committed | v6 pose: `poseest/points` `(n,1,12,2)` `[y,x]`, `poseest/confidence`, `cm_per_pixel` |
| `jabs/annotations/*.json` (3 files) | committed | per-session behavior labels (intervals with `present` true/false) |
| `*.avi` (3 files) | untracked (gitignored) | the matching clip videos, for opening the project in the JABS GUI |
| `README.md` | committed | this file |

The three sessions (selected for label richness, all include `Walking`):

- `LL1-B2B+2016-02-02_BG+LL1-2_C57L_F_90000`
- `LL1-B2B+2016-03-15_SPD+LL1-1_CB6F1_M_90000`
- `LL1-B2B+2018-03-12_SPD+LL1-2_LP_ControlMale-1-PSY_1800`

## How the notebooks use it

The static-page notebooks 00/01/02/03/05 (in `static_build_notebooks/`) auto-detect their data
source: they use the full extracted grooming dataset (`data/zenodo/jabs_grooming/`) if present, and
otherwise fall back to this `data/toy/` sample. CI has only this sample, so it runs here. The JABS
GUI exercise needs the videos below.

## Why videos are untracked

Pose + annotations are small (~8.5 MB total) and safe to commit. The videos are
much larger (~65 MB each) and are only needed for the JABS GUI exercise
(the GUI exercise), which is not run headless in CI. They are gitignored
(`data/toy/*.avi`, `data/toy/*.mp4`) but kept on disk so the project opens in
JABS locally.

## Reproducing this sample

```
# 1. Download the bundle from Zenodo (gitignored output)
python student_scripts/download_zenodo.py --files jabs_single_mouse_behaviors.zip

# 2. Extract it to data/jabs_single_mouse_behaviors/ (pose + annotations + videos)
python student_scripts/download_zenodo.py --extract

# 3. Build the toy sample (copies pose + annotations + matching videos)
python developer/scripts/make_toy_sample.py --n 3
```

## Size constraint

Committed files must stay under GitHub's 100 MB per-file limit (each pose file
is ~3 MB). If committed `data/toy/` ever approaches ~1 GB, switch to Git LFS.
Videos are deliberately untracked to keep the repo small.

## Provenance

Geuther, B., Beane, M., Kumar, V., Choudhary, A. "JABS Behavior Classifier
Example Projects." Zenodo. record 16697331, DOI 10.5281/zenodo.16697331.
License: CC BY-NC 4.0.
