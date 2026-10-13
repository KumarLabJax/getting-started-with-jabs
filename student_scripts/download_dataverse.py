"""Download files from the Kumar Lab's Harvard Dataverse dataset.

Uses the Dataverse Native API via pyDataverse.

Usage:
    python scripts/download_dataverse.py [--manifest scripts/manifest.json]
                                         [--output data/dataverse]
                                         [--dry-run]

The manifest.json file controls which files are downloaded. Edit the "files"
list to add Dataverse file IDs and metadata as the subset is chosen.
"""

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from _netutil import polite_get

DEFAULT_MANIFEST = Path(__file__).parent / "manifest.json"
DEFAULT_OUTPUT = Path(__file__).parent.parent / "data" / "dataverse"


def load_manifest(path: Path) -> dict:
    """Load a manifest JSON file.

    Args:
        path: Path to the manifest.json file.

    Returns:
        The parsed manifest as a dict.
    """
    with open(path) as f:
        return json.load(f)


def _download_one(
    server: str,
    entry: dict,
    output_dir: Path,
    retries: int = 4,
    delay: float = 0.5,
) -> tuple[str, str, str]:
    """Download a single file from the Dataverse server.

    Writes to a .part temp file and renames on success so an interrupted
    download never leaves a truncated file that a later run would treat as
    already present. The shared polite_get adds a descriptive User-Agent, a
    global request throttle, Retry-After handling, and capped backoff.

    Args:
        server: Base URL of the Dataverse server.
        entry: Manifest file entry with "file_id" and "filename" keys.
        output_dir: Directory to write the file into.
        retries: Maximum attempts for the request.
        delay: Minimum seconds between request starts, across threads.

    Returns:
        A tuple (status, filename, detail). Status is "ok" with the file size
        as detail, or "fail" with the error message. Exceptions are caught
        and reported this way rather than raised.
    """
    file_id = entry["file_id"]
    filename = entry["filename"]
    dest = output_dir / filename
    tmp = dest.with_name(dest.name + ".part")
    download_url = f"{server}/api/access/datafile/{file_id}"
    try:
        resp = polite_get(download_url, retries=retries, delay=delay, stream=True)
        with open(tmp, "wb") as out:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    out.write(chunk)
        tmp.replace(dest)
        return ("ok", filename, f"{dest.stat().st_size / 1e6:.1f} MB")
    except Exception as exc:  # noqa: BLE001 - one file's failure must not abort the batch
        tmp.unlink(missing_ok=True)
        return ("fail", filename, str(exc))


def fetch_dataset_readme(manifest: dict, output_dir: Path) -> None:
    """Download the dataset README.md to output_dir/README.md.

    Uses the Dataverse native API to list dataset files and resolve the README
    by label, so no hardcoded file ID is needed. Skips if already present.
    Prints a warning but does not abort on network or API errors.

    Args:
        manifest: Parsed manifest with "server" and "doi" keys.
        output_dir: Directory that receives README.md.
    """
    dest = output_dir / "README.md"
    if dest.exists():
        print("  SKIP  README.md  (already present)")
        return

    server = manifest["server"]
    doi = manifest["doi"]
    list_url = (
        f"{server}/api/datasets/:persistentId/versions/:latest/files"
        f"?persistentId={doi}"
    )

    try:
        resp = polite_get(list_url, retries=3, delay=0.5, accept_json=True)
        file_list = resp.json().get("data", [])
    except Exception as exc:  # noqa: BLE001 - README fetch is best-effort, must not abort the run
        print(f"  WARN  Could not list dataset files: {exc}")
        return

    file_id = None
    for entry in file_list:
        if entry.get("label", "").lower() == "readme.md":
            file_id = entry.get("dataFile", {}).get("id")
            break

    if file_id is None:
        print("  WARN  README.md not found in dataset file listing")
        return

    try:
        resp = polite_get(f"{server}/api/access/datafile/{file_id}", retries=3, delay=0.5)
        dest.write_bytes(resp.content)
        print(f"  OK    README.md  ({dest.stat().st_size / 1e3:.1f} KB)")
    except Exception as exc:  # noqa: BLE001 - README fetch is best-effort, must not abort the run
        print(f"  WARN  README.md download failed: {exc}")


def download_files(
    manifest: dict,
    output_dir: Path,
    dry_run: bool = False,
    workers: int = 3,
    retries: int = 4,
    delay: float = 0.5,
) -> None:
    """Download all manifest files into a directory, in parallel.

    Fetches the dataset README first, then skips files that already exist,
    lists files only in dry-run mode, and downloads the rest with a thread
    pool. Prints one status line per file and a final summary.

    Args:
        manifest: Parsed manifest with "server", "doi", and "files" keys.
        output_dir: Directory to download into; created if missing.
        dry_run: If True, report what would be downloaded without downloading.
        workers: Number of concurrent downloads.
        retries: Maximum attempts per file.
        delay: Minimum seconds between request starts, across workers.

    Raises:
        SystemExit: With status 0 if the manifest has no files, or status 1 if
            any download failed.
    """
    server = manifest["server"]
    files = manifest.get("files", [])

    output_dir.mkdir(parents=True, exist_ok=True)

    # Always fetch the dataset README alongside any data files.
    fetch_dataset_readme(manifest, output_dir)

    if not files:
        print(
            "\nmanifest 'files' list is empty. "
            "Add file entries before running this script."
        )
        sys.exit(0)

    print(f"Downloading {len(files)} file(s) from {server}")
    print(f"Dataset DOI: {manifest['doi']}")
    print(f"Output directory: {output_dir}")
    print(f"Concurrent workers: {workers}\n")

    skipped = 0
    pending = []
    for entry in files:
        dest = output_dir / entry["filename"]
        if dest.exists():
            print(f"  SKIP  {entry['filename']}  ({dest.stat().st_size / 1e6:.1f} MB already present)")
            skipped += 1
        elif dry_run:
            print(f"  DRY   {entry['filename']}  (id={entry['file_id']})")
        else:
            pending.append(entry)

    success, failed = 0, 0
    if pending:
        # Download concurrently - videos and pose files fetch in parallel.
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(_download_one, server, entry, output_dir, retries, delay): entry
                for entry in pending
            }
            for fut in as_completed(futures):
                status, filename, detail = fut.result()
                if status == "ok":
                    print(f"  OK    {filename}  ({detail})")
                    success += 1
                else:
                    print(f"  FAIL  {filename}  - {detail}")
                    failed += 1

    print(f"\nDone: {success} downloaded, {skipped} skipped, {failed} failed.")
    if failed:
        sys.exit(1)


def main() -> None:
    """Parse command-line arguments and download the manifest files."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Path to manifest.json (default: scripts/manifest.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output directory (default: data/dataverse/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be downloaded without downloading",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=3,
        help="Number of concurrent downloads (default: 3; keep modest for a shared archive)",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=4,
        help="Attempts per file before giving up, honoring Retry-After with capped backoff (default: 4)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Minimum seconds between request starts, across workers (default: 0.5)",
    )
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    download_files(
        manifest,
        args.output,
        dry_run=args.dry_run,
        workers=args.workers,
        retries=args.retries,
        delay=args.delay,
    )


if __name__ == "__main__":
    main()
