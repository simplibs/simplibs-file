from pathlib import Path
from typing import NoReturn
from simplibs.exception import AccessError


def raise_file_access_error(
    path: Path,
    operation: str,
    caught_exc: Exception,
) -> NoReturn:
    """Raise AccessError when the OS refuses an operation on one file.

    Args:
        path: The file the operation worked on.
        operation: A single lowercase word naming the operation ("read", "write", "append", "delete", ...).
        caught_exc: The OS-level exception that was caught.
    """

    # 1. Raise structured AccessError wrapping the caught OS exception
    raise AccessError(
        error_name=f"FILE_{operation.upper()}_FAILED",
        label=f"file '{path}'",
        value=str(path),
        problem=(
            f"Failed to {operation} file '{path}'.",
            f"OS reported: {caught_exc}",
        ),
        expected=f"A file the process is allowed to {operation}, on a healthy filesystem.",
        how_to_fix=(
            f"Check that you have permission to {operation} '{path}'.",
            "Make sure no other program (editor, antivirus, indexer) is holding the file open.",
            "Verify that the storage is mounted and has free space.",
        ),
        exception=type(caught_exc),
    )


_DESIGN_NOTES = """
# raise_file_access_error — the OS Said No

## Purpose
The generic single-file OS failure, replacing `raise_write_bytes_error`,
`raise_write_text_error`, `raise_delete_file_error`, `raise_append_text_error`
and friends — their cards differed only in one verb.

## Keeps the Original Exception Type
`exception=type(caught_exc)`, so `except PermissionError` still works for a
caller who wants to react to a specific failure.
"""
