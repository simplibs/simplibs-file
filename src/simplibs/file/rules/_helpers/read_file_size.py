from pathlib import Path


def read_file_size(path: Path) -> int | None:
    """Read the size of a regular file without raising.

    Args:
        path: The path to ask about.

    Returns:
        The size in bytes, or `None` if the path is not a regular file or the
        OS refuses to answer.
    """

    # 1. Only a regular file has a size worth judging
    try:
        if not path.is_file():
            return None

        # 2. One stat, no content read
        return path.stat().st_size

    # 3. A refusal (permissions, bad name) is "no answer"
    except (OSError, ValueError):
        return None


_DESIGN_NOTES = """
# read_file_size — the Never-Raising Twin of `file_size`

## Purpose
`Rule.is_valid` must never raise, and a scan calls it for thousands of files,
so it cannot pay for `@validate_call` or build cards. `None` means "no size"
and is the only non-`int` result (a size is never `None`, so it is a safe marker).
"""
