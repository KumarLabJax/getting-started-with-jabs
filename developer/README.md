# Developer tools

Tools for maintaining the course materials. Nothing here is needed by students.

## Environment setup

```bash
bash developer/setup.sh        # macOS, Linux, Git Bash
developer\setup.bat            # Windows
```

The script creates a virtual environment, installs `requirements.txt` and `requirements-dev.txt`
(ruff, pre-commit, nbmake, papermill), verifies the environment and installs the pre-commit hooks.
Or do it by hand: `python -m venv .venv`, activate it, then `pip install -r requirements.txt -r requirements-dev.txt`.

## `scripts/`

| Script | What it does |
| --- | --- |
| `build_site.py`, `build_site_nav.py`, `render_site_page.py`, `site_manifest.json` | Build the static course site from the notebooks and `docs/templates/` |
| `publish_site.py` | Publish the built site to the `student-landing` branch |
| `make_toy_sample.py` | Build the small committed sample in `data/toy/` |
| `make_keypoint_diagram.py` | Draw the keypoint diagram in `student_notebooks/assets/` |
| `make_pretrained_classifier.py` | Build the fallback grooming classifier and training report in `data/pretrained/` (see the script's docstring) |

## Notebook tests

CI runs the notebooks that work headlessly with `pytest --nbmake` (see `.github/workflows/test_notebooks.yml`).
The launcher scripts are tested by `.github/workflows/test_start_scripts.yml`.

## Layout

- `student_scripts/` (project root): scripts students use, including `prepare_course_data.py`
- `static_build_notebooks/` (project root): the notebooks built into the static course pages (00 to 05)
- `student_notebooks/` (project root): the live demo, deep dives, assets and the cheatsheet
- `developer/` (this folder): tooling for maintainers
