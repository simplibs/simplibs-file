from pathlib import Path
from typing import NoReturn
from simplibs.exception import AlreadyExistsError


def raise_destination_exists_error(
    path: Path,
    operation: str,
) -> NoReturn:
    """Raise AlreadyExistsError when a destination exists and overwriting is not allowed.

    Args:
        path: The existing destination.
        operation: A single lowercase word naming the operation ("copy", "move", "write", ...).
    """

    # 1. Raise structured AlreadyExistsError wrapping a FileExistsError
    raise AlreadyExistsError(
        error_name=f"FILE_{operation.upper()}_DESTINATION_EXISTS",
        label=f"destination '{path}'",
        value=str(path),
        problem=(
            f"Cannot {operation} onto '{path}'.",
            "The destination already exists and overwriting is not allowed.",
        ),
        expected="A destination path that does not exist yet, or overwrite=True.",
        how_to_fix=(
            "Pass overwrite=True if replacing the existing file is intended.",
            "Choose a different destination, or use make_unique_path() from simplibs-path.",
        ),
        exception=FileExistsError,
    )


_DESIGN_NOTES = """
# raise_destination_exists_error — Refusing to Overwrite

## Purpose
Replaces `raise_copy_file_exists_error` and `raise_rename_file_exists_error`
(and the `write_*` equivalents, now that every writer has `overwrite`).
"""
