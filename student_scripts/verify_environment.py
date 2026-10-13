"""Confirm all required packages are installed and the toy data is present.

Exits 0 on success, non-zero on any failure.

Usage:
    python student_scripts/verify_environment.py
"""

import importlib
import shutil
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Package checks
# ---------------------------------------------------------------------------

REQUIRED_PACKAGES = [
    ("numpy", "numpy", "1.24"),
    ("pandas", "pandas", "2.0"),
    ("h5py", "h5py", "3.8"),
    ("matplotlib", "matplotlib", "3.7"),
    ("seaborn", "seaborn", "0.12"),
    ("ipywidgets", "ipywidgets", "8.0"),
    ("opencv-python", "cv2", "4.8"),
    ("jupyterlab", "jupyterlab", "4.0"),
    ("pyDataverse", "pyDataverse", "0.3.2"),
    ("jabs-behavior-classifier", "jabs", "0.47.1"),
]

DEV_PACKAGES = [
    ("ruff", "ruff", "0.4.0"),
    ("pre-commit", "pre_commit", "3.7"),
    ("nbstripout", "nbstripout", "0.7.1"),
    ("papermill", "papermill", "2.5"),
    ("nbmake", "nbmake", "1.5"),
    ("nbconvert", "nbconvert", "7.0"),
    ("pytest", "pytest", "7.0"),
    ("pytest-cov", "pytest_cov", "4.0"),
    ("pytest-xdist", "xdist", "3.0"),
    ("nbformat", "nbformat", "5.0"),
]

COL_W = {"pkg": 30, "ver": 12, "status": 10}
RESET = "\033[0m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"


def _color(text: str, code: str) -> str:
    """Wrap text in an ANSI color code when stdout is a terminal.

    Args:
        text: Text to color.
        code: ANSI escape sequence to prepend (followed by a reset).

    Returns:
        The colored text if stdout is a TTY, otherwise text unchanged.
    """
    return f"{code}{text}{RESET}" if sys.stdout.isatty() else text


def _parse_version(v: str) -> tuple[int, ...]:
    """Parse a dotted version string into a 3-integer tuple.

    Only the first three dot-separated segments are used. Non-digit
    characters in each segment are dropped (so "0rc1" becomes 1), a segment
    with no digits counts as 0, and the result is padded with zeros to
    length 3.

    Args:
        v: Version string such as "3.8.1" or "2.0.0rc1".

    Returns:
        A tuple of three ints suitable for comparison.
    """
    parts = []
    for seg in v.split(".")[:3]:
        try:
            parts.append(int("".join(c for c in seg if c.isdigit()) or "0"))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def _meets_minimum(installed: str, minimum: str) -> bool:
    """Return whether an installed version is at least the minimum version.

    Args:
        installed: Installed version string.
        minimum: Minimum acceptable version string.

    Returns:
        True if installed >= minimum; False if it is lower or if comparing
        the versions raises any exception.
    """
    try:
        return _parse_version(installed) >= _parse_version(minimum)
    except Exception:  # noqa: BLE001 - a malformed version string means "not verified", not a crash
        return False


def check_packages() -> list[tuple[str, str, str, bool]]:
    """Check each package in REQUIRED_PACKAGES for presence and minimum version.

    A package whose version cannot be determined counts as ok.

    Returns:
        A list of (package_name, version, status, ok) tuples. Status is "ok",
        "outdated", or "missing"; version is "-" for a missing package.
    """
    results = []
    for pkg_name, import_name, min_ver in REQUIRED_PACKAGES:
        try:
            mod = importlib.import_module(import_name)
            ver = getattr(mod, "__version__", "unknown")
            ok = ver == "unknown" or _meets_minimum(ver, min_ver)
            results.append((pkg_name, ver, "ok" if ok else "outdated", ok))
        except ImportError:
            results.append((pkg_name, "-", "missing", False))
    return results


def print_package_table(results: list[tuple[str, str, str, bool]]) -> None:
    """Print a table of package check results with colored status markers.

    Args:
        results: Tuples of (package_name, version, status, ok) as returned
            by check_packages or check_dev_packages.
    """
    header = f"{'Package':<{COL_W['pkg']}}{'Installed':<{COL_W['ver']}}{'Status'}"
    print(header)
    print("-" * (COL_W["pkg"] + COL_W["ver"] + 10))
    for pkg, ver, status, ok in results:
        if ok:
            status_str = _color("[OK]", GREEN)
        elif status == "outdated":
            status_str = _color("[OUTDATED]", YELLOW)
        else:
            status_str = _color("[MISSING]", RED)
        print(f"{pkg:<{COL_W['pkg']}}{ver:<{COL_W['ver']}}{status_str}")


# ---------------------------------------------------------------------------
# JABS CLI check
# ---------------------------------------------------------------------------

def _find_console_script(name: str) -> str | None:
    """Locate a console script installed by pip.

    Checks the directory holding the running interpreter first (the venv's
    Scripts/ or bin/), which is where pip installs entry points but which is
    NOT on PATH unless the venv is activated. Falls back to a PATH lookup.

    Args:
        name: Base name of the console script (no extension).

    Returns:
        Absolute path to the executable, or None if not found.
    """
    exe_dir = Path(sys.executable).parent
    for candidate in (exe_dir / name, exe_dir / f"{name}.exe"):
        if candidate.exists():
            return str(candidate)
    return shutil.which(name)


def check_jabs_cli() -> tuple[bool, str]:
    """Confirm the JABS command-line tools are installed.

    Verifies the `jabs` console script exists (next to the interpreter or on
    PATH) and reports the installed package version. Does not invoke the
    `jabs` entry point itself, which is a GUI launcher and prints nothing
    useful for a version check.

    Returns:
        (ok, message) where ok is True when the CLI is installed.
    """
    jabs_path = _find_console_script("jabs")
    if jabs_path is None:
        return False, "jabs command not found (looked next to the interpreter and on PATH)"
    try:
        from importlib.metadata import version

        return True, f"jabs {version('jabs-behavior-classifier')} ({jabs_path})"
    except Exception:  # noqa: BLE001 - version lookup is a nice-to-have, not required for this check
        return True, f"jabs found at {jabs_path}"


# ---------------------------------------------------------------------------
# Toy data check
# ---------------------------------------------------------------------------

TOY_DIR = Path(__file__).parent.parent / "data" / "toy"


def check_toy_data() -> list[tuple[str, bool, str]]:
    """Check that the toy pose and annotation files are present in TOY_DIR.

    Returns:
        A list of (label, ok, detail) tuples. If no pose files are found, a
        single failing entry. Otherwise one entry for the pose files (count
        and total size in MB) and one for the annotation JSON files (ok only
        if at least one exists).
    """
    pose_files = sorted(TOY_DIR.glob("*_pose_est_v6.h5"))
    ann_files = sorted((TOY_DIR / "jabs" / "annotations").glob("*.json"))
    if not pose_files:
        return [("*_pose_est_v6.h5", False, "not found")]
    total_mb = sum(p.stat().st_size for p in pose_files) / 1e6
    return [
        (f"{len(pose_files)} pose file(s)", True, f"{total_mb:.1f} MB"),
        (f"{len(ann_files)} annotation file(s)", len(ann_files) > 0, "jabs/annotations/"),
    ]


def print_toy_table(results: list[tuple[str, bool, str]]) -> None:
    """Print toy data check results with colored status markers.

    Args:
        results: Tuples of (label, ok, detail) as returned by check_toy_data.
    """
    for fname, ok, detail in results:
        icon = _color("[OK]", GREEN) if ok else _color("[MISSING]", RED)
        print(f"  {icon}  {fname}  ({detail})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def check_dev_packages() -> list[tuple[str, str, str, bool]]:
    """Check each package in DEV_PACKAGES for presence and minimum version.

    A package whose version cannot be determined counts as ok.

    Returns:
        A list of (package_name, version, status, ok) tuples. Status is "ok",
        "outdated", or "missing"; version is "-" for a missing package.
    """
    results = []
    for pkg_name, import_name, min_ver in DEV_PACKAGES:
        try:
            mod = importlib.import_module(import_name)
            ver = getattr(mod, "__version__", "unknown")
            ok = ver == "unknown" or _meets_minimum(ver, min_ver)
            results.append((pkg_name, ver, "ok" if ok else "outdated", ok))
        except ImportError:
            results.append((pkg_name, "-", "missing", False))
    return results


def main() -> int:
    """Run all environment checks and print a report with fix hints.

    Checks core packages, dev tools, the JABS CLI, and the toy data. Missing
    or outdated dev tools are informational only and do not count as
    failures.

    Returns:
        0 if all checks passed, otherwise 1.
    """
    failures = 0

    print("\n=== Core Packages ===\n")
    pkg_results = check_packages()
    print_package_table(pkg_results)
    pkg_failures = [r for r in pkg_results if not r[3]]
    if pkg_failures:
        print()
        for pkg, _, status, _ in pkg_failures:
            if status == "missing":
                print(f"  Fix: pip install {pkg}")
            else:
                print(f"  Fix: pip install --upgrade {pkg}")
        failures += len(pkg_failures)
    failed_pkg = len(pkg_failures)
    total_pkg = len(pkg_results)
    summary = f"\n{total_pkg - failed_pkg}/{total_pkg} packages verified."
    print(_color(summary, GREEN if failed_pkg == 0 else RED))

    print("\n=== Dev Tools ===\n")
    dev_results = check_dev_packages()
    print_package_table(dev_results)
    dev_failures = [r for r in dev_results if not r[3]]
    if dev_failures:
        print()
        missing_pkgs = [pkg for pkg, _, status, _ in dev_failures if status == "missing"]
        if missing_pkgs:
            print(f"  Fix: pip install {' '.join(missing_pkgs)}")
        outdated_pkgs = [pkg for pkg, _, status, _ in dev_failures if status == "outdated"]
        if outdated_pkgs:
            print(f"  Fix: pip install --upgrade {' '.join(outdated_pkgs)}")
    failed_dev = len(dev_failures)
    total_dev = len(dev_results)
    summary_dev = f"{total_dev - failed_dev}/{total_dev} dev tools verified."
    print(_color(summary_dev, GREEN if failed_dev == 0 else YELLOW))

    print("\n=== JABS CLI ===\n")
    jabs_ok, jabs_msg = check_jabs_cli()
    if jabs_ok:
        print(_color(f"  [OK] {jabs_msg}", GREEN))
    else:
        print(_color(f"  [MISSING] {jabs_msg}", RED))
        print("  Fix: pip install jabs-behavior-classifier==0.47.1")
        print("  macOS: brew install libomp  (required for XGBoost)")
        failures += 1

    print("\n=== Toy Data ===\n")
    if not TOY_DIR.exists():
        print(
            _color(
                f"  [WARN] {TOY_DIR} not found - check that your clone completed successfully",
                YELLOW,
            )
        )
        failures += 1
    else:
        toy_results = check_toy_data()
        print_toy_table(toy_results)
        toy_failures = [r for r in toy_results if not r[1]]
        if toy_failures:
            print(
                _color(
                    "\n  Toy data files missing - re-clone the repo or ask the course staff.",
                    YELLOW,
                )
            )
            failures += len(toy_failures)

    # Dev tools (ruff, pytest, ...) are optional for students - requirements-dev.txt
    # is explicitly "Developer tools (optional)" per the README - so a missing dev
    # tool is informational only and must not fail this check or tell a student
    # their environment is broken when it isn't.
    print()
    total_failures = failures
    if total_failures == 0:
        print(_color("All checks passed. You are ready to run the notebooks.", GREEN))
        return 0
    else:
        print(
            _color(
                f"{total_failures} check(s) failed. Fix the issues above before proceeding.",
                RED,
            )
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
