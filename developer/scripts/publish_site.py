"""Build the full student site from dev and write it into a student-landing checkout.

Besides the site pages, this writes the other files students need (scripts, toy
and dense-GT data, license) into the checkout of the student-landing branch.

Notebooks are NOT executed here: each page is rendered from the outputs already
committed in its .ipynb (run papermill locally first, review, and commit - see
"How to Publish" in developer/README.md). A notebook with code cells but no
saved outputs is a hard error, so an unexecuted notebook can never ship.

Usage:
    python developer/scripts/publish_site.py --target ../student-landing-checkout
    python developer/scripts/publish_site.py --target some/dir --dry-run

Only paths on the allowlist below are written or removed in --target, so dev-only
files can never leak into student-landing.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

import nbformat

sys.path.insert(0, str(Path(__file__).parent))
from build_site import build_nav as manifest_nav  # noqa: E402
from build_site_nav import build_nav as apply_site_nav  # noqa: E402
from render_site_page import DEFAULT_SOURCE_DIR, render_page  # noqa: E402

REPO = Path(__file__).parent.parent.parent
MANIFEST = Path(__file__).parent / "site_manifest.json"
TEMPLATES = REPO / "docs" / "templates"

INDEX_REDIRECT = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="0; url=00_setup_and_orientation.html">
<link rel="canonical" href="00_setup_and_orientation.html">
<title>Getting Started with JABS</title>
</head>
<body>
<p>Redirecting to <a href="00_setup_and_orientation.html">Setup and Orientation</a>...</p>
</body>
</html>
"""

# Static pages: template -> published name (nav/next buttons are filled in afterwards).
STATIC_PAGES = {
    "live_demo_landing.html": "live_demo.html",
    "live_demo_jabs_gui_walkthrough.html": "live_demo_jabs_gui_walkthrough.html",
}

# Everything publish_site.py owns in the target. Anything else there is left alone.
OWNED = [
    "docs",
    "student_notebooks/live_demo/jabs-demo.ipynb",
    "student_notebooks/assets",
    "student_notebooks/cheatsheet/jabs_cheatsheet.pdf",
    "student_scripts",
    "config/zenodo",
    "data/pretrained",
    "data/README.md",
    "data/toy",
    "data/dense_gt_a1",
    "data/dense_gt_a2",
    "slides/JABS_module_companion_deck.pptx",
    "requirements.txt",
    "LICENSE",
    ".gitattributes",
    ".github/ISSUE_TEMPLATE",
    # GitHub only dispatches workflows present on the default branch (student-landing).
    ".github/workflows/publish_student_landing.yml",
]


# Files that live under a different name in the target: dev source -> path in student-landing.
# The branch's front page and gitignore differ from dev's, so their sources are kept in developer/landing/.
RENAMED = {
    "developer/landing/README.md": "README.md",
    "developer/landing/gitignore": ".gitignore",
}


def check_executed(notebook: Path) -> None:
    """Ensure a notebook has saved outputs so an unexecuted one cannot ship.

    Args:
        notebook: Path to the .ipynb file to check.

    Raises:
        SystemExit: If the notebook has code cells but none has any outputs.
    """
    nb = nbformat.read(str(notebook), as_version=4)
    code = [c for c in nb.cells if c.cell_type == "code"]
    if code and not any(c.get("outputs") for c in code):
        raise SystemExit(f"[ERROR] {notebook.relative_to(REPO)} has code cells but no saved outputs - execute and commit it first.")


def build_to(out: Path) -> None:
    """Build the complete docs site into a directory.

    Copies the shared template assets, renders every manifest notebook (after
    check_executed), copies the static pages and the live demo notebook,
    writes index.html (a redirect) and .nojekyll, then applies the sidebar nav
    and next buttons to all pages.

    Args:
        out: Directory to build into; created if missing. It must not already
            contain _shared or live_demo, since those are created without
            overwriting.

    Raises:
        SystemExit: If any manifest notebook has no saved outputs.
    """
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    out.mkdir(parents=True, exist_ok=True)
    shutil.copytree(TEMPLATES / "_shared", out / "_shared")
    for entry in manifest:
        nb_path = REPO / entry["notebook"]
        check_executed(nb_path)
        render_page(nb_path, entry["title"], entry.get("eyebrow", ""), manifest_nav(manifest, entry["slug"]),
                    out / f"{entry['slug']}.html", DEFAULT_SOURCE_DIR)
    for template, name in STATIC_PAGES.items():
        shutil.copy2(TEMPLATES / template, out / name)
    (out / "index.html").write_text(INDEX_REDIRECT, encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    demo = REPO / "student_notebooks" / "live_demo" / "jabs-demo.ipynb"
    (out / "live_demo").mkdir()
    shutil.copy2(demo, out / "live_demo" / "jabs-demo.ipynb")
    apply_site_nav(out)


# Folders JABS creates inside a project (features, caches, trained classifiers, ...)
# whenever the GUI or CLI opens it. They are gitignored on dev but sit on disk, so
# they must not be copied into the published branch.
JABS_GENERATED = {"archive", "cache", "classifiers", "features", "predictions", "session", "training_logs"}


def skip_generated(directory: str, names: list[str]) -> list[str]:
    """Tell shutil.copytree to skip the folders JABS generates inside a project.

    Args:
        directory: The directory copytree is currently listing.
        names: The names in that directory.

    Returns:
        The names to leave out: JABS-generated folders directly inside a `jabs/` folder.
    """
    if Path(directory).name != "jabs":
        return []
    return [name for name in names if name in JABS_GENERATED]


def sync(built_docs: Path, target: Path, dry_run: bool) -> None:
    """Copy the built docs and every other OWNED path into the target checkout.

    Existing destinations are removed before being replaced. Prints one line
    per path.

    Args:
        built_docs: Directory holding the freshly built site, written to
            "docs" in the target.
        target: Root of the student-landing checkout.
        dry_run: If True, only print what would be written and change nothing.
    """
    def put(src: Path, rel: str) -> None:
        """Replace target/rel with a copy of src, or just report it in a dry run.

        Args:
            src: File or directory to copy.
            rel: Destination path relative to the target checkout.
        """
        dest = target / rel
        print(f"{'would write' if dry_run else 'write'}: {rel}")
        if dry_run:
            return
        if dest.exists():
            shutil.rmtree(dest) if dest.is_dir() else dest.unlink()
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dest, ignore=skip_generated)
        else:
            shutil.copy2(src, dest)

    put(built_docs, "docs")
    for rel in OWNED[1:]:
        put(REPO / rel, rel)
    for src_rel, dest_rel in RENAMED.items():
        put(REPO / src_rel, dest_rel)


def main() -> None:
    """Parse arguments, then build the site in a staging directory and sync it.

    The staging directory is a hidden sibling of --target and is always
    removed afterwards.

    Raises:
        SystemExit: If --target is not a git checkout.
    """
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", type=Path, required=True, help="checkout of the student-landing branch")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not (args.target / ".git").exists():
        raise SystemExit(f"[ERROR] {args.target} is not a git checkout")
    staging = args.target.parent / f".{args.target.name}-docs-staging"
    if staging.exists():
        shutil.rmtree(staging)
    try:
        build_to(staging)
        sync(staging, args.target, args.dry_run)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


if __name__ == "__main__":
    main()
