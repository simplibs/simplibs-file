from pathlib import Path
from simplibs.path import PathLike, normalize_path
# Outers
from ..validations import (
    raise_file_access_error,
    raise_file_not_found_error,
    raise_not_a_file_error,
)


def resolve_source_file(
    path: PathLike,
    operation: str,
) -> Path:
    """Normalize a path and guarantee it points to an existing regular file.

    Args:
        path: The file an operation is about to read.
        operation: A single lowercase word naming the operation, used in the failure card.

    Returns:
        The normalized, verified file `Path` (symlinks resolved).

    Raises:
        NotFoundError: If nothing exists at the path.
        StateError: If the path is not a regular file.
        AccessError: If the OS refuses even the existence check.
    """

    # 1. Normalize — a symlink is followed, because the CONTENT is wanted
    normalized_path = normalize_path(path)

    # 2. Ask the disk; a refusal is an access problem, not "missing"
    try:
        exists = normalized_path.exists()
        is_file = exists and normalized_path.is_file()
    except OSError as caught_exc:
        raise_file_access_error(normalized_path, operation, caught_exc)

    # 3. Nothing there
    if not exists:
        raise_file_not_found_error(normalized_path, operation)

    # 4. Something there, but not a regular file
    if not is_file:
        raise_not_a_file_error(normalized_path, operation)

    # 5. A verified file
    return normalized_path


_DESIGN_NOTES = """
# resolve_source_file — "This Is a File I Can Work With"

## Purpose
The existence + type check repeated at the top of eight old functions, in one
place. Replaces the `exists()` / `is_file()` / `raise_*_not_found_error` /
`raise_*_not_a_file_error` block in `read_bytes`, `read_text`, `read_lines`,
`read_json`, `copy_file`, `backup_file`, ...

## Content, Not Entry
`normalize_path` follows symlinks, so this helper answers "is the CONTENT
behind this path a file?". Operations on the directory entry itself
(`delete_file`, `move_file`) must NOT use it — they use `normalize_entry_path`,
because a dangling link is a perfectly deletable entry.

## Why Not `ensure_file(create=False)`
Its failure text talks about `create=False`, which would confuse the reader of
a plain `read_text` error.

## `exists()` Can Raise
`Path.exists()` propagates `PermissionError` for some paths; that is reported
as an `AccessError` card, not a bare traceback.
"""
