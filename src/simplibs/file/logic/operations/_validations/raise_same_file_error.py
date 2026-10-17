from pathlib import Path
from typing import NoReturn
from simplibs.exception import ParamError


def raise_same_file_error(
    path: Path,
    operation: str,
) -> NoReturn:
    """Raise ParamError when source and destination are the same file.

    Args:
        path: The shared path.
        operation: A single lowercase word naming the operation ("copy", "backup", ...).
    """

    # 1. Raise structured ParamError — the argument combination is unusable
    raise ParamError(
        error_name=f"FILE_{operation.upper()}_SAME_FILE",
        label="destination",
        value=str(path),
        problem=f"Source and destination of the {operation} are the same file: '{path}'.",
        expected="A destination different from the source.",
        how_to_fix=(
            "Choose another destination path.",
            "Check whether a symlink makes two different-looking paths point to one file.",
        ),
        exception=ValueError,
    )


_DESIGN_NOTES = """
# raise_same_file_error — Source Equals Destination

## Purpose
Copying a file onto itself would truncate it in the old implementation.
The comparison is made on normalized paths (symlinks resolved), so a link
and its target count as the same file.

## Includes `backup_file`
With `timestamp=False` and an empty `suffix`, the backup path equals the
source — a parameter mistake reported by this card.
"""
