"""Render an executed student notebook into a styled site page.

The page matches the docs/templates/_shared/ design system, instead of
nbconvert's default theme.

Uses nbconvert's "basic" template, which emits only the raw per-cell HTML
fragment (no <html>/<head>, no CSS of its own) - full control is the point,
since docs/templates/_shared/design-system.css section 7 ("Rendered notebook
content") already carries the styling for every class that template emits.
This script's job is just to run that conversion and drop the fragment into
the same page shell (sidebar + hero) the hand-authored template pages use.

Page navigation (the sidebar's list of pages) is a parameter, not something
this script decides - the site's actual page breakdown is still being worked
out. Pass --nav-json pointing at a small JSON file of
[{"href": "...", "label": "...", "active": true|false}, ...] once that's
settled; without it, a single-item "This page" nav is used so the script is
still usable standalone (e.g. for a proof-of-concept single page).

Usage:
    # 1. Execute the notebook first (papermill):
    papermill static_build_notebooks/00_setup_and_orientation.ipynb \
        /tmp/00_setup_and_orientation_executed.ipynb

    # 2. Render it into a styled site page:
    python developer/scripts/render_site_page.py \
        /tmp/00_setup_and_orientation_executed.ipynb \
        --title "Setup and Orientation" \
        --eyebrow "Notebook 00" \
        --output docs/notebooks/00_setup_and_orientation.html
"""

import argparse
import json
import re
import shutil
from pathlib import Path

import nbformat
from nbconvert import HTMLExporter

REPO = Path(__file__).parent.parent.parent
DEFAULT_SOURCE_DIR = REPO / "student_notebooks"

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} - Getting Started with JABS</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="_shared/design-system.css">
<link rel="stylesheet" href="_shared/pygments.css">
</head>
<body>

<div class="page">

  <aside class="sidebar" id="sidebar">
    <div class="sidebar-head">
      <span class="sidebar-brand sidebar-label">From Pose to Behavior: A Hands-On Introduction to JABS</span>
      <button class="sidebar-toggle" id="sidebarToggle" aria-label="Toggle sidebar">&lsaquo;</button>
    </div>
    <nav class="sidebar-nav">
{nav_links}
    </nav>
    <div class="sidebar-footer sidebar-label">Short Course on the Application of Machine Learning for Automated Quantification of Behavior<br>JAX &middot; Oct 11&ndash;16, 2026</div>
  </aside>

  <div class="main">

    <div class="hero">
{eyebrow_html}      <h1>{title}</h1>
    </div>

    <section>
      <div class="nb-body">
{body}
      </div>
    </section>

    <div class="page-footer">
      <span><a href="https://www.kumarlab.org/">Kumar Lab</a> &middot; <a href="https://www.jax.org/">The Jackson Laboratory</a> &middot; <a href="https://www.jax.org/education-and-learning/education-calendar/2026/10-october/machine-learning-for-automated-quantification-of-behavior-short-course">Short Course on the Application of Machine Learning for Automated Quantification of Behavior</a></span>
      <span>Oct 11&ndash;16, 2026</span>
    </div>

  </div>
</div>

<script src="_shared/site.js"></script>
<script>
  JabsSite.initSidebarToggle();
  JabsSite.initScrollToTop();
</script>

</body>
</html>
"""

DEFAULT_NAV = [{"href": "#", "label": "This page", "active": True}]


def render_notebook_body(notebook_path: Path) -> str:
    """Convert an executed notebook to the raw nbconvert "basic"-template fragment.

    Args:
        notebook_path: Path to the .ipynb file to convert.

    Returns:
        The HTML fragment for the notebook cells (no <html>/<head> wrapper).
    """
    nb = nbformat.read(str(notebook_path), as_version=4)
    exporter = HTMLExporter(template_name="basic")
    body, _resources = exporter.from_notebook_node(nb)
    return body


_IMG_SRC_RE = re.compile(r'(<img[^>]+src=")([^"]+)(")')


def localize_markdown_assets(body: str, notebook_path: Path, source_dir: Path, output_path: Path) -> str:
    """Copy local <img> assets next to the rendered page and rewrite their src.

    Handles non-data-URI images from markdown (e.g. ![](assets/x.svg)), so they
    still resolve once this page lives somewhere other than the original
    notebook's own directory.

    Papermill's execution copies the notebook (and its still-relative markdown
    image paths) into a different build location - e.g. running
    `static_build_notebooks/01_data_ingestion.ipynb` through papermill into
    `docs/notebooks/01_data_ingestion_executed.ipynb`, at which point
    `assets/keypoint_diagram.svg` (relative to the original notebook) no
    longer resolves relative to the executed copy's own new location.
    Resolves each reference against notebook_path's own directory first (in
    case a deep-dive notebook keeps assets alongside itself), then against
    source_dir/assets (the shared location, e.g. student_notebooks/assets/).

    Copied files go into an "assets" folder beside output_path (created if
    needed). Sources that are data:, http://, or https:// URLs are left
    alone, and unresolvable sources are left as-is with a printed warning.

    Args:
        body: HTML fragment containing <img> tags.
        notebook_path: Path of the notebook the body came from; its directory
            is searched first for each asset.
        source_dir: Fallback directory searched for each asset path.
        output_path: Path of the page being written; assets are copied beside it.

    Returns:
        The HTML with each resolved <img> src rewritten to "assets/<filename>".
    """
    assets_dir = output_path.parent / "assets"

    def _replace(match: re.Match) -> str:
        """Localize the src of one matched <img> tag if it can be resolved.

        Args:
            match: Match with groups for the tag prefix, the src, and the suffix.

        Returns:
            The rewritten tag text, or the original text for remote, data, or
            unresolvable sources.
        """
        prefix, src, suffix = match.group(1), match.group(2), match.group(3)
        if src.startswith(("data:", "http://", "https://")):
            return match.group(0)

        candidates = [notebook_path.parent / src, source_dir / src]
        source_file = next((c for c in candidates if c.exists()), None)
        if source_file is None:
            print(f"  [WARN] could not resolve image asset: {src} (tried {[str(c) for c in candidates]})")
            return match.group(0)

        assets_dir.mkdir(parents=True, exist_ok=True)
        dest = assets_dir / source_file.name
        shutil.copy2(source_file, dest)
        return f'{prefix}assets/{source_file.name}{suffix}'

    return _IMG_SRC_RE.sub(_replace, body)


def render_nav(nav_items: list[dict]) -> str:
    """Render sidebar nav items as HTML anchor lines.

    Args:
        nav_items: Dicts with "href" and "label" keys and an optional
            "active" flag that marks the current page.

    Returns:
        Newline-joined <a> tags, one per item.
    """
    lines = []
    for item in nav_items:
        cls = "active sidebar-label" if item.get("active") else "sidebar-label"
        lines.append(f'      <a href="{item["href"]}" class="{cls}">{item["label"]}</a>')
    return "\n".join(lines)


def render_page(
    notebook_path: Path, title: str, eyebrow: str, nav_items: list[dict], output_path: Path, source_dir: Path
) -> None:
    """Render a notebook into a complete styled site page and write it to disk.

    Creates the parent directory of output_path if needed, copies any local
    image assets beside the page, and prints a "Saved" line.

    Args:
        notebook_path: Path to an already-executed .ipynb file.
        title: Text for the page <title> and <h1>.
        eyebrow: Small label above the title; omitted from the page if empty.
        nav_items: Sidebar nav items, as accepted by render_nav.
        output_path: Where to write the HTML page (UTF-8).
        source_dir: Fallback directory for markdown-referenced image assets.
    """
    body = render_notebook_body(notebook_path)
    body = localize_markdown_assets(body, notebook_path, source_dir, output_path)
    eyebrow_html = f'      <div class="eyebrow">{eyebrow}</div>\n' if eyebrow else ""
    page = PAGE_TEMPLATE.format(
        title=title,
        eyebrow_html=eyebrow_html,
        nav_links=render_nav(nav_items),
        body=body,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(page, encoding="utf-8")
    print(f"Saved {output_path}")


def main() -> None:
    """Parse command-line arguments and render the given notebook to a page.

    Sidebar nav items come from the --nav-json file if given, else DEFAULT_NAV.
    """
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("notebook", type=Path, help="path to an already-executed .ipynb")
    parser.add_argument("--title", required=True, help="page <h1> / <title> text")
    parser.add_argument("--eyebrow", default="Getting Started with JABS", help="small label above the title")
    parser.add_argument("--nav-json", type=Path, default=None,
                         help="path to a JSON file of [{href, label, active}, ...] sidebar nav items - "
                              "defaults to a single 'This page' item if omitted")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR,
                         help="where to look for markdown-referenced assets (e.g. assets/x.svg) if they "
                              "aren't found next to the (possibly relocated, papermill-executed) notebook "
                              f"itself - default: {DEFAULT_SOURCE_DIR}")
    args = parser.parse_args()

    nav_items = DEFAULT_NAV
    if args.nav_json is not None:
        nav_items = json.loads(args.nav_json.read_text(encoding="utf-8"))

    render_page(args.notebook, args.title, args.eyebrow, nav_items, args.output, args.source_dir)


if __name__ == "__main__":
    main()
