# Getting Started with JABS (dev)

**Short Course on the Application of Machine Learning for Automated Quantification of Behavior · JAX · October 11–16, 2026 · The Jackson Laboratory, Bar Harbor, ME**

This is the **dev** branch: the notebooks and build tooling that produce the course site. If
you're a student looking for the course itself, you want the
[`student-landing`](../../tree/student-landing) branch instead - the built site plus the one
notebook you actually run, with none of this branch's build tooling.

## What's Here vs. What Ships

This module is a precomputed, read-only site (built from the notebooks in
`static_build_notebooks/`) plus one runnable hands-on notebook. The site covers:

- **Setup and Orientation** - what JABS is, how the module is organized
- **Data Ingestion** - explore real pose data from the Zenodo JABS example dataset
- **Precomputed Tracking & QC** - assess pose quality across many sessions
- **Annotation and Classification with JABS** - the annotate/train/classify loop, and how to
  install JABS and open a project
- **Results and Analysis** - turn classifier output into ethograms and statistics
- **Deep Dives** (optional) - Pose Estimation concepts, the Harvard Dataverse dataset, and how
  to apply this pipeline to your own recordings
- **Live Workflow** - `student_notebooks/live_demo/jabs-demo.ipynb`, the one notebook students
  run, plus its GUI walkthrough companion page

Only the built site and `jabs-demo.ipynb` ship to students, on `student-landing`. Everything
else here - the source notebooks for the static pages, `developer/` build tooling -
stays dev-only.

## How to Publish

Source of truth is this branch. `student-landing` is generated from it - never edit the built
`docs/` there by hand, because the next publish overwrites it.

1. **Edit** the notebooks in `static_build_notebooks/` (or the static pages in `docs/templates/`).
2. **Execute and save outputs** for any notebook with code cells, against real data (papermill
   auto-detects the full Zenodo dataset if present, else falls back to `data/toy/`). Notebook 04
   needs the JABS GUI and has no code cells, so it ships as written:
   ```bash
   python -m papermill static_build_notebooks/01_data_ingestion.ipynb        static_build_notebooks/01_data_ingestion.ipynb
   ```
3. **Review and commit** the executed notebooks here on `dev`. CI never re-runs notebooks, so
   what is committed is exactly what students see. `publish_site.py` refuses to build a notebook
   that has code cells but no saved outputs.
4. **Preview locally** (optional): `python developer/scripts/build_site.py` renders into
   `docs/site_preview/` (gitignored); then `python developer/scripts/build_site_nav.py`.
5. **Publish** with the manual GitHub Action: Actions -> "Publish to student-landing" -> Run
   workflow. Leave `dry_run` on first to see the changed files, then run again with it off. It
   commits to `student-landing` as `docs: publish from dev @ <sha>`.
   Locally, the same thing is `python developer/scripts/publish_site.py --target <path to a
   student-landing checkout>`, after which you commit and push there yourself.

What gets written to `student-landing` (everything else on that branch is left alone): `README.md` and `.gitignore` (sources in `developer/landing/`), `docs/`, `student_notebooks/live_demo/jabs-demo.ipynb`, `student_notebooks/assets/`, `student_notebooks/cheatsheet/jabs_cheatsheet.pdf`,
`student_scripts/`, `config/zenodo/`, `data/README.md`, `data/toy/`, `data/pretrained/`, `data/dense_gt_a1/`, `requirements.txt`, `LICENSE`, `.gitattributes`, and the publish workflow file. To ship a new
kind of file, add it to `OWNED` in `developer/scripts/publish_site.py`. The page list, titles
and order live in `developer/scripts/site_manifest.json` and `build_site_nav.py`.

## Quick Start (One Click)

The launchers in `student_scripts/` do everything: create `.venv`, install requirements, and run
`student_scripts/prepare_course_data.py`, which downloads the Zenodo grooming dataset (~110 MB, once),
builds the practice set under `data/zenodo_scrubbed/` (the 10 shortest of the 25 Zenodo videos; about half keep
their original labels, the rest are unlabeled for hands-on labeling) and caches features with
`jabs-init`, so the first Train in the GUI does not stall. Then they open the JABS GUI and the demo
notebook in JupyterLab. Each step is skipped if it is already done, and an existing practice set is
never rebuilt, so labels you made are kept.

| Platform | Double-click | Or from a terminal |
|----------|--------------|--------------------|
| Windows | `student_scripts\start_jabs.bat` | `.\student_scripts\start_jabs.ps1` |
| macOS | `student_scripts/start_jabs.command` | `./student_scripts/start_jabs.sh` |
| Linux | - | `./student_scripts/start_jabs.sh` |

Options: `-NoGui` / `-NoNotebook` / `-SkipData` (PowerShell) or `--no-gui` / `--no-notebook` /
`--skip-data` (shell). `-SkipData` works offline and falls back to the bundled toy data. On
macOS the first run also installs `libomp` through Homebrew if it is available. Prerequisite:
Python 3.10+ on your PATH. If macOS blocks the `.command` file, right-click it and choose Open
once. On a minimal Linux install the JABS GUI also needs the Qt system libraries, for example
`sudo apt-get install libegl1 libgl1 libxkbcommon0 libdbus-1-3 libfontconfig1` (Debian/Ubuntu).

## Local Development

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
python student_scripts/verify_environment.py

jupyter lab
```

### Data

- **Primary**: the Zenodo "JABS Behavior Classifier Example Projects" deposit
  ([`doi:10.5281/zenodo.16697331`](https://doi.org/10.5281/zenodo.16697331)) -
  `python student_scripts/download_zenodo.py --files jabs_grooming.zip --extract`
- **Optional deep dive**: the Harvard Dataverse open-field dataset
  ([`doi:10.7910/DVN/SAPNJG`](https://doi.org/10.7910/DVN/SAPNJG)) -
  `python student_scripts/download_dataverse.py`
- **Toy sample**: `data/toy/` is committed for CI-free local testing and fresh clones
- **Dense ground truth**: `data/dense_gt_a1/` (session 2010, hand-reviewed, ~99% coverage) is held
  out entirely from training and used only to evaluate classifier metrics - not regenerated by
  any download script. `data/dense_gt_a2/` holds a second annotation pass of the same session. See
  `data/README.md`.
- **Fallback classifier**: `data/pretrained/` holds a classifier trained on the Zenodo grooming set
  (without session 2010) and its training report. The live demo uses it when you have not trained
  one in the GUI.

## Repository Structure

```
getting-started-with-jabs (dev branch)/
├── static_build_notebooks/
│   └── 00-05_*.ipynb        # Source for the static site pages
├── student_notebooks/
│   ├── deep_dives/          # Pose Estimation, Dataverse Dataset, Your Own Data!
│   ├── live_demo/           # jabs-demo.ipynb - the one notebook students run
│   └── cheatsheet/          # Printable two-sided handout
├── student_scripts/          # download/verify/prepare-project scripts (student-facing)
├── developer/                 # Build tooling: render_site_page.py, publish_site.py - dev-only
├── config/                    # Download-manifest configs (zenodo/)
├── data/toy/                  # Small committed sample; everything else downloaded/gitignored
├── data/dense_gt_a1/, a2/     # Session 2010, two annotation passes (held-out test set)
├── data/pretrained/           # Fallback grooming classifier and its training report
├── docs/templates/            # Hand-authored pages + the shared design system (CSS/JS)
├── requirements.txt            # Student runtime
├── requirements-dev.txt        # ruff, papermill, nbmake, pre-commit
└── README.md                   # This file
```

## Branch Model

- **`dev`** (this branch) - notebooks + build tooling; the source the student site is generated from. Students don't need it.
- **`student-landing`** - the built static site (`docs/`) plus `jabs-demo.ipynb`, `student_scripts/`,
  and the toy + dense-GT data. No dev tooling; its only workflow is a copy of the publish workflow, because GitHub can only dispatch workflows on the default branch. This is the default branch and
  what GitHub Pages serves. Generated from `dev` - see [How to Publish](#how-to-publish).

This repo lives in the public `KumarLabJax` org. Students use the `student-landing` branch;
`dev` is there for anyone who wants the source notebooks the static pages are built from.

## Tech Stack

| Component | Tool | Version |
|-----------|------|---------|
| Language | Python | 3.10+ |
| Environment | venv + pip | - |
| Notebooks | JupyterLab | ≥4.0 |
| Behavior classification | JABS | 0.47.1 |
| ML backbone | XGBoost | (via JABS) |
| Plotting | matplotlib + seaborn | ≥3.7 + ≥0.12 |
| Linting | Ruff | ≥0.4.0 |

Pose estimation is precomputed for this course - keypoints come from the Kumar Lab's
`mouse-tracking-runtime` pipeline, run ahead of time on every video. The Pose Estimation deep
dive covers this conceptually; no pose model is trained as part of the course.

## Citations

**JABS tool:** Choudhary, A., Geuther, B. Q., Sproule, T. J., Beane, G., Kohar, V., Trapszo, J.,
& Kumar, V. "JAX Animal Behavior System (JABS), a genetics-informed, end-to-end advanced
behavioral phenotyping platform for the laboratory mouse." eLife 107259 (2026).

**Zenodo example dataset:** Geuther, B., Beane, M., Kumar, V., Choudhary, A. "JABS Behavior
Classifier Example Projects." Zenodo, 2025. `doi:10.5281/zenodo.16697331`

**Harvard Dataverse dataset:** Kumar, Vivek; Brian Geuther; Sean Deats, 2024, "The Jackson
Laboratory (JAX) - Kumar Lab Mouse Strain Survey of Behavior in the Open Field Arena (Video
Dataset)," `doi:10.7910/DVN/SAPNJG`, Harvard Dataverse, V1.

## License

The code in this repository is released under the MIT License, the same license as the
[JABS behavior classifier](https://github.com/KumarLabJax/JABS-behavior-classifier) - see
[LICENSE](LICENSE). The datasets are not covered by it and keep their own terms (CC BY-NC(-SA)
4.0; see `data/README.md`) and citations.

## AI Use Disclosure

Parts of this repository were developed with the assistance of generative AI tools (Claude, by
Anthropic, used via Claude Code). AI assistance was used for drafting and editing course
content (notebooks and the built site), writing and refactoring helper scripts in
`student_scripts/` and `developer/`, and documentation. All AI-assisted output was reviewed,
tested, and edited by the course developers, who remain responsible for the content. The
datasets (Zenodo and Harvard Dataverse) are real, publicly available data and were not
generated by AI.

## Contact

`jabs@jax.org` for JABS-specific questions; the course staff for everything else.
