# Getting Started with JABS

**Short Course on the Application of Machine Learning for Automated Quantification of Behavior · JAX · October 11–16, 2026 · The Jackson Laboratory, Bar Harbor, ME**

A hands-on module teaching end-to-end behavioral phenotyping using real, publicly available
mouse data: pose data structure, quality control, and behavior classification with JABS (the
JAX Animal Behavior System).

## The Site

Everything but the hands-on exercise is a precomputed, read-only site - open `docs/index.html`
in a browser, or view it published via GitHub Pages once enabled for this repo. It covers:

- **Setup and Orientation** - what JABS is, how this module is organized
- **Data Ingestion** - explore real pose data from the Zenodo JABS example dataset
- **Precomputed Tracking & QC** - assess pose quality across many sessions
- **Annotation and Classification with JABS** - the annotate/train/classify loop, and how to
  install JABS and open a project
- **Results and Analysis** - turn classifier output into ethograms and statistics
- **Deep Dives** (optional) - Pose Estimation concepts, the Harvard Dataverse dataset, and how
  to apply this pipeline to your own recordings

## The Hands-On Exercise

The one notebook you actually run is `student_notebooks/live_demo/jabs-demo.ipynb` - either
live, in person on a course VM (JABS already installed), or async and self-paced on your own
machine. It recaps the pose-data and QC concepts covered on the site, hands off to the JABS
desktop app for labeling and training, then evaluates the classifier you trained against a
held-out, densely labeled session.

A two-sided printable cheatsheet for the labeling session (shortcuts, menus, metrics) is in
`student_notebooks/cheatsheet/jabs_cheatsheet.pdf`, and the companion slides are in
`slides/JABS_module_companion_deck.pptx`.

### Quick Start (One Click)

Prerequisite: Python 3.10+ on your PATH. Then clone the repo and launch:

| Platform | Double-click | Or from a terminal |
|----------|--------------|--------------------|
| Windows | `student_scripts\start_jabs.bat` | `.\student_scripts\start_jabs.ps1` |
| macOS | `student_scripts/start_jabs.command` | `./student_scripts/start_jabs.sh` |
| Linux | - | `./student_scripts/start_jabs.sh` |

```bash
git clone <this-repo-url>
cd getting-started-with-jabs
./student_scripts/start_jabs.sh          # Windows: .\student_scripts\start_jabs.ps1
```

The first run takes several minutes. It creates `.venv`, installs the requirements (on macOS
it also installs `libomp` via Homebrew if available), and runs
`student_scripts/prepare_course_data.py`, which downloads the Zenodo grooming dataset (~110 MB),
builds the practice set in `data/zenodo_scrubbed/` for hands-on labeling in the JABS GUI, and
caches features with `jabs-init` so the first Train does not stall. Then it opens the JABS GUI and
opens `jabs-demo.ipynb` in JupyterLab. Later runs skip whatever is already done, and an existing
practice set is never rebuilt, so labels you made are kept. Options: `-NoGui` / `-NoNotebook` /
`-SkipData` (PowerShell) or `--no-gui` / `--no-notebook` / `--skip-data` (shell). `-SkipData`
works offline using the bundled toy data. If macOS blocks the `.command` file, right-click it
and choose Open once.

### Manual Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python student_scripts/verify_environment.py
python student_scripts/prepare_course_data.py   # download the data and cache features

jupyter lab
# open student_notebooks/live_demo/jabs-demo.ipynb
```

A small toy dataset is committed under `data/toy/` so the verification script works right after
cloning, with no download required. The dense, hand-reviewed ground-truth session used for
classifier evaluation (`data/dense_gt_a1/`, with a second annotation pass in `data/dense_gt_a2/`)
is also committed, since it isn't reproducible from any download script. `data/pretrained/` holds
a fallback classifier and its training report, used by the notebook if you have not trained one
in the GUI.

### Your Own Data

Want to run this pipeline on your own open-field-arena recordings instead of the course
dataset? See the "Your Own Data!" deep dive on the site - it covers the recording setup, pose
estimation, and how to plug in your own project.

## Data

- **Primary dataset**: the Zenodo "JABS Behavior Classifier Example Projects" deposit
  ([`doi:10.5281/zenodo.16697331`](https://doi.org/10.5281/zenodo.16697331)) - downloaded on
  demand via `student_scripts/download_zenodo.py`, not committed (except the small toy sample).
- **Optional deep dive**: the Harvard Dataverse open-field dataset
  ([`doi:10.7910/DVN/SAPNJG`](https://doi.org/10.7910/DVN/SAPNJG)) - see `data/README.md` and
  `student_scripts/download_dataverse.py`.

## Requirements

- Python 3.10+
- ~4 GB disk space (dependencies, the Zenodo download, and the cached features); the toy data
  alone needs far less
- macOS: `brew install libomp` (XGBoost requirement)

## Source and Updates

This branch is generated. The notebooks the site pages are built from, the build tooling, and
the publishing steps live on the [`dev`](../../tree/dev) branch (see "How to Publish" in its
README). Changes are made there and published here, so edits made directly on this branch will
be overwritten.

## AI Use Disclosure

Parts of this repository were developed with the assistance of generative AI tools (Claude, by
Anthropic, used via Claude Code). AI assistance was used for drafting and editing course
content on the site, writing and refactoring helper scripts in `student_scripts/`, and
documentation. All AI-assisted output was reviewed, tested, and edited by the course
developers, who remain responsible for the content. The datasets (Zenodo and Harvard Dataverse)
are real, publicly available data and were not generated by AI.

If you find an error, please open an issue or contact the course staff.

## License

The code in this repository is released under the MIT License, the same license as the
[JABS behavior classifier](https://github.com/KumarLabJax/JABS-behavior-classifier) - see
[LICENSE](LICENSE). The datasets are not covered by it and keep their own terms (CC BY-NC(-SA)
4.0; see `data/README.md`) and citations.

## Questions

`jabs@jax.org` for JABS-specific questions (see the JABS GUI walkthrough on the site); the
course staff for everything else.
