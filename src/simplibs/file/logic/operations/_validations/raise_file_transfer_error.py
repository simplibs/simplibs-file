from pathlib import Path
from typing import NoReturn
from simplibs.exception import AccessError


def raise_file_transfer_error(
    source: Path,
    destination: Path,
    operation: str,
    caught_exc: Exception,
) -> NoReturn:
    """Raise AccessError when the OS refuses an operation that moves content between two files.

    Args:
        source: The file the content comes from.
        destination: The file the content goes to.
        operation: A single lowercase word naming the operation ("copy", "move", "backup").
        caught_exc: The OS-level exception that was caught.
    """

    # 1. Raise structured AccessError wrapping the caught OS exception
    raise AccessError(
        error_name=f"FILE_{operation.upper()}_FAILED",
        label=f"file '{source}' -> '{destination}'",
        value=str(destination),
        problem=(
            f"Failed to {operation} '{source}' to '{destination}'.",
            f"OS reported: {caught_exc}",
        ),
        expected=f"A readable source and a destination location where the process may {operation} to.",
        how_to_fix=(
            "Check read permission for the source and write permission for the destination folder.",
            "Make sure no other program is holding either file open.",
            "Verify that the destination storage has free space.",
        ),
        exception=type(caught_exc),
    )


_DESIGN_NOTES = """
# raise_file_transfer_error — the OS Said No, Two Paths Involved

## Purpose
`raise_file_access_error` names one file; `copy_file`, `move_file` and
`backup_file` have a source and a destination, and the card must show both.
Added to the planned list during batch 0.
"""
