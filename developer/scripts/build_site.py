"""Build every styled site page in one pass for fast local previews.

This is the fast local iteration loop for working on notebook content and
immediately seeing the rendered result.

Local preview tool; the published site is built by publish_site.py. This script is
for previewing content changes against the real design system while the
site's page structure/nav is still being worked out. Once that's settled,
this (or its logic) can replace the CI steps.

Reads developer/scripts/site_manifest.json - a list of
{notebook, slug, title, eyebrow} entries, one per page. The manifest's order
and titles ARE today's placeholder page breakdown (mirrors the old NB00/01/
02/03/05 numbering, NB04 excluded - it needs the JABS GUI
and can't run headlessly). Edit the manifest directly as the real page
breakdown gets designed - nothing else needs to change to pick that up.

For each entry:
  1. Execute the notebook fresh via papermill.
  2. Render it into a styled page via render_site_page.py's logic, with a
     sidebar nav built from every OTHER entry in the manifest too - so this
     produces one coherent multi-page site, not isolated single pages.

Usage:
    python developer/scripts/build_site.py
    python developer/scripts/build_site.py --manifest my_manifest.json --output-dir docs/site_preview
    python developer/scripts/build_site.py --only 01_data_ingestion  # just one page, fast iteration
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

import papermill

sys.path.insert(0, str(Path(__file__).parent))
from render_site_page import DEFAULT_SOURCE_DIR, render_page  # noqa: E402

REPO = Path(__file__).parent.parent.parent
DEFAULT_MANIFEST = Path(__file__).parent / "site_manifest.json"
DEFAULT_OUTPUT_DIR = REPO / "docs" / "site_preview"


def load_manifest(path: Path) -> list[dict]:
    """Load the site manifest from a JSON file.

    Args:
        path: Path to the manifest JSON file (UTF-8).

    Returns:
        The list of manifest entries, each a dict with notebook, slug, title,
        and (optionally) eyebrow keys.
    """
    return json.loads(path.read_text(encoding="utf-8"))


def build_nav(manifest: list[dict], active_slug: str) -> list[dict]:
    """Build the sidebar nav items for a page from the manifest.

    Args:
        manifest: Manifest entries, in display order.
        active_slug: Slug of the page being rendered; its item is marked active.

    Returns:
        One dict per manifest entry with "href" ("<slug>.html"), "label" (the
        entry title), and "active" (True only for the active slug).
    """
    return [
        {"href": f"{entry['slug']}.html", "label": entry["title"], "active": entry["slug"] == active_slug}
        for entry in manifest
    ]


def build_site(manifest_path: Path, output_dir: Path, only: str | None) -> None:
    """Execute and render the notebooks listed in the manifest into a site.

    Recreates output_dir/_shared from docs/templates/_shared, executes each
    notebook with papermill into output_dir/_executed, renders each to
    output_dir/<slug>.html, and prints progress for every page.

    Args:
        manifest_path: Path to the manifest JSON file.
        output_dir: Directory to write the rendered site into (created if needed).
        only: If given, build only the manifest entry with this slug.

    Raises:
        SystemExit: If `only` is given and matches no manifest entry.
    """
    manifest = load_manifest(manifest_path)
    entries = [e for e in manifest if only is None or e["slug"] == only]
    if not entries:
        raise SystemExit(f"No manifest entry matches --only {only!r}")

    output_dir.mkdir(parents=True, exist_ok=True)
    shared_dest = output_dir / "_shared"
    if shared_dest.exists():
        shutil.rmtree(shared_dest)
    shutil.copytree(REPO / "docs" / "templates" / "_shared", shared_dest)

    executed_dir = output_dir / "_executed"
    executed_dir.mkdir(parents=True, exist_ok=True)

    for entry in entries:
        notebook_path = REPO / entry["notebook"]
        executed_path = executed_dir / f"{entry['slug']}_executed.ipynb"
        output_path = output_dir / f"{entry['slug']}.html"

        print(f"[{entry['slug']}] executing {notebook_path.relative_to(REPO)} ...")
        papermill.execute_notebook(str(notebook_path), str(executed_path), progress_bar=False)

        print(f"[{entry['slug']}] rendering -> {output_path.relative_to(REPO)}")
        nav_items = build_nav(manifest, entry["slug"])
        render_page(
            executed_path, entry["title"], entry.get("eyebrow", "Getting Started with JABS"),
            nav_items, output_path, DEFAULT_SOURCE_DIR,
        )

    print(f"\nDone. Open {output_dir / entries[0]['slug']}.html to preview.")


def main() -> None:
    """Parse command-line arguments (--manifest, --output-dir, --only) and build the site."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--only", default=None, help="build just one page by its manifest 'slug', for fast iteration")
    args = parser.parse_args()
    build_site(args.manifest, args.output_dir, args.only)


if __name__ == "__main__":
    main()
