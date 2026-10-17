import os
import time
from pathlib import Path


def replace_with_retry(
    source: Path,
    destination: Path,
    *,
    attempts: int = 5,
    delay: float = 0.05,
) -> None:
    """Atomically replace `destination` with `source`, retrying short Windows locks.

    Args:
        source: The file to move into place.
        destination: The path it becomes.
        attempts: How many times to try on Windows when the destination is momentarily locked.
            At least one try is always made, so a value below 1 means a single try.
        delay: Base pause in seconds between attempts; grows with every attempt.

    Raises:
        OSError: If the replacement fails (a permission problem, a lock that
            outlasts every attempt, a directory at the destination, another device).
    """

    # 1. Every try but the last: on Windows a short lock (antivirus, indexer) is waited out
    for attempt in range(1, attempts):
        try:
            os.replace(source, destination)
            return
        except PermissionError:
            if os.name != "nt":
                raise
            time.sleep(delay * attempt)

    # 2. The last try — the only one for `attempts <= 1`; its failure is final, anything else fails at once
    os.replace(source, destination)


_DESIGN_NOTES = """
# replace_with_retry — `os.replace` That Survives Windows Flakiness

## Purpose
`os.replace` onto a file that an antivirus or the search indexer holds for a
few milliseconds fails with `PermissionError`. Up to `attempts` tries with a
growing pause (`delay * attempt`, 0.75 s in total by default) hide it.
Elsewhere a `PermissionError` is real and raised at once.

## The Last Try Stands Outside the Loop
The final attempt is made after the loop, so the function can never end without
either replacing the file or raising — not even for `attempts=0`, which would
otherwise skip the loop and return silently with nothing done. At least one try
is always made.

## Shared
Extracted from `commit_draft` so that `move_file` retries the same way.
"""
