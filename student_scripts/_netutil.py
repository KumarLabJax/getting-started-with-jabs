"""Shared helpers for polite HTTP access to public data archives.

Project standard for client-side API calls (see the "nice-api-client" memory):
identify ourselves with a descriptive User-Agent, self-rate-limit with a global
minimum spacing between request starts (across threads), honor the server's
Retry-After on 429/403, and retry transient failures with capped exponential
backoff. Download callers add atomic .part writes and skip-existing so transfers
are resumable. Both download_dataverse.py and download_zenodo.py use this.
"""

import threading
import time

import requests

USER_AGENT = "getting-started-with-jabs course data tool (Kumar Lab JABS course)"
RETRY_STATUS = {403, 429, 500, 502, 503, 504}  # 403/429 = archive rate limiting
MAX_BACKOFF = 60.0

# Global request throttle shared across worker threads: no two requests start
# closer together than the configured minimum interval.
_throttle_lock = threading.Lock()
_next_allowed_at = [0.0]


def throttle(min_interval: float) -> None:
    """Block until at least `min_interval` seconds have passed since the last start.

    Args:
        min_interval: Minimum spacing in seconds between request starts. A
            value of zero or less disables throttling.
    """
    if min_interval <= 0:
        return
    with _throttle_lock:
        now = time.monotonic()
        if now < _next_allowed_at[0]:
            time.sleep(_next_allowed_at[0] - now)
        _next_allowed_at[0] = time.monotonic() + min_interval


def polite_get(
    url: str,
    retries: int = 5,
    delay: float = 1.0,
    stream: bool = False,
    accept_json: bool = False,
    extra_headers: dict | None = None,
):
    """Fetch a URL with a descriptive UA, global throttle, Retry-After, and capped backoff.

    Args:
        url: URL to fetch.
        retries: max attempts before giving up.
        delay: minimum seconds between request starts (global, across threads).
        stream: pass through to requests (for large downloads).
        accept_json: send Accept: application/json (some APIs 403 without it).
        extra_headers: optional additional headers.

    Returns:
        A successful requests.Response.

    Raises:
        RuntimeError: if all attempts fail.
    """
    headers = {"User-Agent": USER_AGENT}
    if accept_json:
        headers["Accept"] = "application/json"
    if extra_headers:
        headers.update(extra_headers)

    last = None
    for attempt in range(1, retries + 1):
        throttle(delay)
        try:
            resp = requests.get(url, headers=headers, stream=stream, timeout=300)
            if resp.status_code in RETRY_STATUS and attempt < retries:
                retry_after = resp.headers.get("Retry-After", "")
                wait = float(retry_after) if retry_after.isdigit() else min(2 ** attempt, MAX_BACKOFF)
                last = f"HTTP {resp.status_code}"
                print(f"  (rate-limited; waiting {wait:.0f}s before retry)")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            last = str(exc)
            if attempt < retries:
                time.sleep(min(2 ** attempt, MAX_BACKOFF))
    raise RuntimeError(f"GET failed after {retries} attempts: {url} ({last})")
