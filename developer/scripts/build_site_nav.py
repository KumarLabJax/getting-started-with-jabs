"""Post-process rendered site pages to add the shared nav and next-page buttons.

Adds the shared sidebar nav (with per-page table of contents) and branching
"next page" buttons, then writes the result back in place.

Run this after render_site_page.py has (re-)rendered whichever pages
changed - it rewrites every page's <nav class="sidebar-nav"> block and
"next" button(s) from the PAGES/NEXT_PAGE tables below, so the site's page
list and reading order live in exactly one place instead of being repeated
by hand across every page.

Usage:
    python developer/scripts/build_site_nav.py [--site-dir docs/site_preview]

Each page also gets a per-page table of contents built from its own <h2>
headings (nbconvert gives every heading a stable id) - including fixing a
real nbconvert quirk where multiple headings with the same text (e.g.
several "Check In" sections) collide on the same id and silently break
anchor links for everything after the first.
"""

import argparse
import html
import re
from collections import Counter
from pathlib import Path

MAIN_PAGES = [
    ("00_setup_and_orientation.html", "Setup and Orientation"),
    ("01_data_ingestion.html", "Data Ingestion"),
    ("03_precomputed_tracking.html", "Precomputed Tracking & QC"),
    ("04_jabs_classification.html", "Annotation and Classification with JABS"),
    ("05_results_and_analysis.html", "Results and Analysis"),
]

LIVE_WORKFLOW = [
    ("live_demo.html", "JABS Demo"),
    ("live_demo_jabs_gui_walkthrough.html", "JABS GUI Walkthrough"),
]

DEEP_DIVES = [
    ("02_pose_estimation.html", "Pose Estimation"),
    ("deep_dive_dataverse.html", "Dataverse Dataset"),
    ("deep_dive_your_data.html", "Your Own Data!"),
]

GROUPS = [
    (None, MAIN_PAGES),
    ("Live Workflow", LIVE_WORKFLOW),
    ("Deep Dives", DEEP_DIVES),
]

ALL_PAGES = MAIN_PAGES + LIVE_WORKFLOW + DEEP_DIVES

# Reading-order "next" link(s) - each value is a list of (href, label, style)
# options. Most pages have exactly one ("primary"); the points where the main
# sequence and the Live Workflow branch meet get two, since there isn't one
# single correct "next" there. Deep Dives and the last page of each chain
# get none.
NEXT_PAGE = {
    href: [(MAIN_PAGES[i + 1][0], MAIN_PAGES[i + 1][1], "primary")]
    for i, (href, _) in enumerate(MAIN_PAGES[:-1])
}
NEXT_PAGE["04_jabs_classification.html"] = [
    ("05_results_and_analysis.html", "Continue: Results and Analysis", "primary"),
    ("live_demo.html", "Try it live: JABS Demo", "secondary"),
]
NEXT_PAGE["live_demo.html"] = [
    ("live_demo_jabs_gui_walkthrough.html", "Next: JABS GUI Walkthrough", "primary"),
    ("05_results_and_analysis.html", "Skip to: Results and Analysis", "secondary"),
]
NEXT_PAGE["live_demo_jabs_gui_walkthrough.html"] = [
    ("05_results_and_analysis.html", "Continue: Results and Analysis", "primary"),
]
NEXT_PAGE["05_results_and_analysis.html"] = [
    ("live_demo.html", "Explore: JABS Demo (Live Workflow)", "primary"),
    ("02_pose_estimation.html", "Explore: Deep Dives", "secondary"),
]

NAV_RE = re.compile(r'(<nav class="sidebar-nav">\n)(.*?)(\n    </nav>)', re.S)
PAGE_FOOTER_RE = re.compile(r'(\s*)<div class="page-footer"')
H2_RE = re.compile(r'<h2 id="([^"]+)">(.*?)<a class="anchor-link" href="#[^"]+">')


def dedupe_h2_ids(content: str) -> str:
    """Make every <h2> id in a page unique.

    nbconvert gives every <h2> an id derived from its text - duplicate
    headings (e.g. several 'Check In' sections) collide on the same id,
    which breaks anchor links (the browser only ever reaches the first
    one). Number repeats -2, -3, ... in both the id and its self-link.

    Args:
        content: Full HTML text of a rendered page.

    Returns:
        The HTML with repeated heading ids and their anchor-link hrefs
        renumbered; the first occurrence of each id is unchanged.
    """
    seen: Counter[str] = Counter()

    def repl(m: re.Match) -> str:
        """Renumber a matched heading's id and href if its id was seen before.

        Args:
            m: Match for one <h2> through its anchor-link href.

        Returns:
            The matched text, with id and href suffixed -N for the Nth repeat.
        """
        base_id = m.group(1)
        seen[base_id] += 1
        n = seen[base_id]
        new_id = base_id if n == 1 else f"{base_id}-{n}"
        return m.group(0).replace(f'id="{base_id}"', f'id="{new_id}"', 1).replace(
            f'href="#{base_id}"', f'href="#{new_id}"', 1
        )

    return re.sub(r'<h2 id="([^"]+)">.*?<a class="anchor-link" href="#\1">', repl, content, flags=re.S)


def extract_headings(content: str) -> list[tuple[str, str]]:
    """Extract the <h2> headings of a page for its table of contents.

    Args:
        content: Full HTML text of a rendered page.

    Returns:
        A list of (heading_id, heading_text) tuples in document order, with
        HTML tags stripped and entities unescaped from the text.
    """
    return [
        (hid, html.unescape(re.sub(r"<[^>]+>", "", text)))
        for hid, text in H2_RE.findall(content)
    ]


def build_nav(site_dir: Path) -> None:
    """Rewrite the sidebar nav and "next" buttons of every site page in place.

    For each page in ALL_PAGES found in site_dir, dedupes <h2> ids, replaces
    the sidebar nav block (with a table of contents under the active page),
    removes any previous "page-next" block, and inserts a new one before the
    page footer when NEXT_PAGE has options for that page. Missing pages are
    skipped, and warnings are printed when the nav block or footer cannot be
    matched. Each page file is overwritten and a progress line is printed.

    Args:
        site_dir: Directory of already-rendered site pages to update.
    """
    for slug, _ in ALL_PAGES:
        path = site_dir / slug
        if not path.exists():
            print(f"[SKIP] {slug}: not found")
            continue
        content = path.read_text(encoding="utf-8")
        content = dedupe_h2_ids(content)
        headings = extract_headings(content)

        toc_html = ""
        if headings:
            items = "\n".join(
                f'        <li><a href="#{hid}">{text}</a></li>' for hid, text in headings
            )
            toc_html = f'\n      <ul class="sidebar-toc sidebar-label">\n{items}\n      </ul>'

        lines = []
        for heading, pages in GROUPS:
            if heading:
                lines.append(f'      <div class="sidebar-heading sidebar-label">{heading}</div>')
            for href, label in pages:
                cls = "active sidebar-label" if href == slug else "sidebar-label"
                lines.append(f'      <a href="{href}" class="{cls}">{label}</a>')
                if href == slug:
                    lines.append(toc_html.strip("\n"))
        new_nav = "\n".join(line for line in lines if line)
        content, n = NAV_RE.subn(lambda m: m.group(1) + new_nav + m.group(3), content)
        if n != 1:
            print(f"[WARN] {slug}: nav block substitution count = {n}")

        # Drop any "Next" block from a previous run before deciding whether to
        # add one - otherwise re-running this script keeps stacking duplicates.
        content = re.sub(r'\n?\s*<div class="page-next">.*?</div>\n', "\n", content, flags=re.S)
        next_options = NEXT_PAGE.get(slug)
        next_n = 0
        if next_options:
            buttons = "\n".join(
                f'      <a class="btn-{style}" href="{href}">{label} &rarr;</a>'
                for href, label, style in next_options
            )
            next_block = f'\n    <div class="page-next">\n{buttons}\n    </div>\n'
            content, next_n = PAGE_FOOTER_RE.subn(
                next_block + r"\1" + '<div class="page-footer"', content, count=1
            )
            if next_n != 1:
                print(f"[WARN] {slug}: page-footer not found, could not add Next button")

        path.write_text(content, encoding="utf-8")
        print(f"updated nav in {slug} ({len(headings)} TOC entries" + (", +next" if next_n else "") + ")")


def main() -> None:
    """Parse the --site-dir argument and update the nav of the pages there."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--site-dir", type=Path, default=Path("docs/site_preview"),
        help="directory of already-rendered site pages to update in place (default: docs/site_preview)",
    )
    args = parser.parse_args()
    build_nav(args.site_dir)


if __name__ == "__main__":
    main()
