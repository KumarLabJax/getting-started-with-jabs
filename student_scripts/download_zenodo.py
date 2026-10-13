"""Download files from a Zenodo record, mirroring download_dataverse.py.

Used to pull the course's canonical dataset: the published Zenodo deposit
"JABS Behavior Classifier Example Projects" (record 16697331; the
jabs_single_mouse_behaviors / grooming / turn / social example projects).

Usage:
    python student_scripts/download_zenodo.py
        [--config config/zenodo/annotation_sets.yaml]
        [--record 16697331] [--output data/zenodo]
        [--files jabs_single_mouse_behaviors.zip,jabs_grooming.zip]
        [--workers 2] [--delay 1.0] [--retries 5] [--dry-run] [--extract]

By default the script reads config/zenodo/annotation_sets.yaml to determine
which annotation-set zips to download. Edit that file to uncomment the sets
you want - you do not need to touch this script. Pass --files to override the
config entirely with an explicit comma-separated list.

Public Zenodo records need no auth. The file list is fetched from the REST API
(GET /api/records/<id> with Accept: application/json), then each file downloads
with atomic .part writes and skip-existing (resumable).

Be-nice-to-Zenodo design (Zenodo enforces a per-session request rate limit and
returns 403/429 when exceeded):
  - low default concurrency (2 workers),
  - a global client-side throttle that spaces ALL request starts at least
    --delay seconds apart (across workers), so we self-limit below the cap,
  - honors the server's Retry-After header, with capped exponential backoff as
    a fallback.
"""

import argparse
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from _netutil import polite_get

DEFAULT_RECORD = "16697331"
DEFAULT_OUTPUT = Path(__file__).parent.parent / "data" / "zenodo"
DEFAULT_CONFIG = Path(__file__).parent.parent / "config" / "zenodo" / "annotation_sets.yaml"
ZENODO_API = "https://zenodo.org/api/records"


def load_config(path: Path) -> set[str]:
    """Read annotation_sets.yaml and return the set of zip filenames to download.

    Prints a clear message and exits if the file is missing, unparseable, or
    has no enabled annotation sets (all commented out).

    Args:
        path: Path to the annotation_sets.yaml config file.

    Returns:
        The set of zip filenames listed under `annotation_sets`.

    Raises:
        SystemExit: With status 1 if the file is not found, cannot be parsed
            as YAML, or lists no annotation sets.
    """
    import yaml

    try:
        with open(path) as f:
            cfg = yaml.safe_load(f) or {}
    except FileNotFoundError:
        print(f"Config not found: {path}")
        print("Pass --files to specify annotation sets explicitly.")
        sys.exit(1)
    except yaml.YAMLError as exc:
        print(f"Could not parse config {path}: {exc}")
        sys.exit(1)

    sets = cfg.get("annotation_sets") or []
    if not sets:
        print(f"No annotation sets enabled in {path}.")
        print("Uncomment at least one entry under 'annotation_sets:' and re-run.")
        sys.exit(1)
    return set(sets)


def fetch_record(record_id: str, retries: int, delay: float) -> dict:
    """Return the Zenodo record JSON, including its file list.

    Args:
        record_id: Zenodo record id.
        retries: Maximum attempts for the request.
        delay: Minimum seconds between request starts.

    Returns:
        The parsed JSON record as a dict.
    """
    return polite_get(f"{ZENODO_API}/{record_id}", retries=retries, delay=delay, accept_json=True).json()


def _download_url(file_entry: dict, record_id: str) -> str:
    """Resolve a file's content download URL across Zenodo link-schema variants.

    Args:
        file_entry: One entry from the record's file list.
        record_id: Zenodo record id, used to build a fallback URL.

    Returns:
        The `links.content` URL if present, else `links.self`, else a URL
        built from the API base, record id, and the file's key.
    """
    links = file_entry.get("links", {}) or {}
    return (
        links.get("content")
        or links.get("self")
        or f"{ZENODO_API}/{record_id}/files/{file_entry['key']}/content"
    )


def _download_one(
    file_entry: dict, record_id: str, output_dir: Path, retries: int, delay: float
) -> tuple[str, str, str]:
    """Download one file to a .part temp, then rename on success.

    Streams the file in 64 KiB chunks. Any exception is caught so one failure
    does not abort the batch; the partial .part file is deleted in that case.

    Args:
        file_entry: One entry from the record's file list (needs a `key`).
        record_id: Zenodo record id.
        output_dir: Directory the file is written into.
        retries: Maximum attempts for the request.
        delay: Minimum seconds between request starts.

    Returns:
        A (status, key, detail) tuple. Status is "ok" with the size in MB as
        detail, or "fail" with the error message as detail.
    """
    key = file_entry["key"]
    dest = output_dir / key
    tmp = dest.with_name(dest.name + ".part")
    try:
        resp = polite_get(_download_url(file_entry, record_id), retries=retries, delay=delay, stream=True)
        with open(tmp, "wb") as out:
            for chunk in resp.iter_content(chunk_size=1 << 16):
                if chunk:
                    out.write(chunk)
        tmp.replace(dest)
        return ("ok", key, f"{dest.stat().st_size / 1e6:.1f} MB")
    except Exception as exc:  # noqa: BLE001 - one file's failure must not abort the batch
        tmp.unlink(missing_ok=True)
        return ("fail", key, str(exc))


def download_record(
    record_id: str,
    output_dir: Path,
    wanted: set | None = None,
    dry_run: bool = False,
    workers: int = 2,
    delay: float = 1.0,
    retries: int = 5,
    extract: bool = False,
) -> None:
    """Download the wanted files of a Zenodo record, skipping existing ones.

    Fetches the record's file list, optionally filters it, then downloads the
    pending files concurrently into output_dir (created if needed). Files that
    already exist are skipped. Prints per-file progress and a final summary.
    Optionally extracts downloaded .zip archives into output_dir afterwards.

    Args:
        record_id: Zenodo record id.
        output_dir: Directory to download into.
        wanted: If given and non-empty, only download files whose key is in
            this set.
        dry_run: If True, list what would be downloaded without downloading
            or extracting.
        workers: Number of concurrent download threads.
        delay: Minimum seconds between request starts, across workers.
        retries: Maximum attempts per request.
        extract: If True, unzip every .zip file present into output_dir
            (not done when dry_run is set).

    Raises:
        SystemExit: With status 1 if no files in the record match `wanted`,
            or if any download fails.
    """
    record = fetch_record(record_id, retries, delay)
    files = record.get("files", [])
    title = record.get("metadata", {}).get("title", "")
    if wanted:
        files = [f for f in files if f["key"] in wanted]
    if not files:
        print("No matching files in record (check --files keys).")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Zenodo record {record_id}: {title}")
    print(f"Output directory: {output_dir}")
    print(f"Workers: {workers} | min request spacing: {delay}s\n")

    skipped, pending = 0, []
    for f in files:
        dest = output_dir / f["key"]
        if dest.exists():
            print(f"  SKIP  {f['key']}  ({dest.stat().st_size / 1e6:.1f} MB already present)")
            skipped += 1
        elif dry_run:
            print(f"  DRY   {f['key']}  ({f.get('size', 0) / 1e6:.1f} MB)")
        else:
            pending.append(f)

    success, failed = 0, 0
    if pending:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(_download_one, f, record_id, output_dir, retries, delay): f
                for f in pending
            }
            for fut in as_completed(futures):
                status, key, detail = fut.result()
                if status == "ok":
                    print(f"  OK    {key}  ({detail})")
                    success += 1
                else:
                    print(f"  FAIL  {key}  - {detail}")
                    failed += 1

    print(f"\nDone: {success} downloaded, {skipped} skipped, {failed} failed.")

    if extract and not dry_run:
        for f in files:
            archive = output_dir / f["key"]
            if archive.suffix == ".zip" and archive.exists():
                print(f"  extracting {archive.name} ...")
                with zipfile.ZipFile(archive) as zf:
                    zf.extractall(output_dir)

    if failed:
        sys.exit(1)


def main() -> None:
    """Parse command-line arguments and download the requested Zenodo files.

    Uses the explicit --files list if given, otherwise the annotation sets
    enabled in the --config YAML file.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--record", default=DEFAULT_RECORD,
        help=f"Zenodo record id (default: {DEFAULT_RECORD}, the JABS example projects)",
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT,
        help="Output directory (default: data/zenodo/)",
    )
    parser.add_argument(
        "--config", type=Path, default=DEFAULT_CONFIG,
        help=(
            f"Path to annotation_sets.yaml (default: {DEFAULT_CONFIG}). "
            "Edit that file to choose which zips to download."
        ),
    )
    parser.add_argument(
        "--files", default=None,
        help=(
            "Comma-separated zip keys to download, e.g. "
            "jabs_grooming.zip,jabs_turn.zip. "
            "Overrides --config when given."
        ),
    )
    parser.add_argument(
        "--workers", type=int, default=2,
        help="Concurrent downloads (default: 2; kept low to respect Zenodo's rate limit)",
    )
    parser.add_argument(
        "--delay", type=float, default=1.0,
        help="Minimum seconds between request starts, across workers (default: 1.0)",
    )
    parser.add_argument(
        "--retries", type=int, default=5,
        help="Attempts per request, honoring Retry-After with capped backoff (default: 5)",
    )
    parser.add_argument("--dry-run", action="store_true", help="List what would be downloaded")
    parser.add_argument("--extract", action="store_true", help="Unzip downloaded .zip files into the output dir")
    args = parser.parse_args()

    if args.files:
        wanted = {s.strip() for s in args.files.split(",")}
    else:
        wanted = load_config(args.config)
        print(f"Config: {args.config}")
        print(f"Annotation sets: {', '.join(sorted(wanted))}\n")
    download_record(
        args.record, args.output,
        wanted=wanted, dry_run=args.dry_run,
        workers=args.workers, delay=args.delay, retries=args.retries, extract=args.extract,
    )


if __name__ == "__main__":
    main()
