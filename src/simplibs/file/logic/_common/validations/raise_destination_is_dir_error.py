from pathlib import Path
from typing import NoReturn
from simplibs.exception import StateError


def raise_destination_is_dir_error(
    path: Path,
    operation: str,
) -> NoReturn:
    """Raise StateError when a destination path is an existing directory.

    Args:
        path: The destination that turned out to be a directory.
        operation: A single lowercase word naming the operation ("copy", "move", "write", ...).
    """

    # 1. Raise structured StateError wrapping an IsADirectoryError
    raise StateError(
        error_name=f"FILE_{operation.upper()}_DESTINATION_IS_DIRECTORY",
        label=f"destination '{path}'",
        value=str(path),
        problem=(
            f"Cannot {operation} onto '{path}'.",
            "A directory already occupies this path.",
        ),
        expected="A destination that is a file path — existing or not — never an existing directory.",
        how_to_fix=(
            "Give the full target path including the file name, e.g. 'folder/name.ext'.",
            "Choose a different name if a directory of that name must stay.",
        ),
        exception=IsADirectoryError,
    )


_DESIGN_NOTES = """
# raise_destination_is_dir_error — a Directory Where a File Should Go

## Purpose
`shutil.copy2(src, folder)` copies *into* the folder, while the old
`copy_file` returned the path of the folder — a silent mismatch. The new
functions treat the destination as a file path and refuse an existing
directory with this card.
"""
