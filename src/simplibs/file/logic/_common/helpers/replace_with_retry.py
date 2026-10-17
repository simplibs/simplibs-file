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
        delay: Base pause in seconds between attempts; grows with every attempt.

    Raises:
        OSError: If the replacement fails (a permission problem, a lock that
            outlasts every attempt, a directory at the destination, another device).
    """

    # 1. Try; on Windows a short lock (antivirus, indexer) is retried, anything else fails at once
    for attempt in range(1, attempts + 1):
        try:
            os.replace(source, destination)
            return
        except PermissionError:
            if os.name != "nt" or attempt == attempts:
                raise
            time.sleep(delay * attempt)


_DESIGN_NOTES = """
# replace_with_retry — `os.replace` That Survives Windows Flakiness

## Purpose
`os.replace` onto a file that an antivirus or the search indexer holds for a
few milliseconds fails with `PermissionError`. Up to `attempts` tries with a
growing pause (`delay * attempt`, 0.75 s in total by default) hide it.
Elsewhere a `PermissionError` is real and raised at once.

## Shared
Extracted from `commit_draft` so that `move_file` retries the same way.

## TODO(test)
Succeeds on the third try on "nt"; raises after `attempts`; a single attempt on POSIX.
"""
