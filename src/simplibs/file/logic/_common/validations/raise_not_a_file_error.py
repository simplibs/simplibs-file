from pathlib import Path
from typing import NoReturn
from simplibs.exception import StateError


def raise_not_a_file_error(
    path: Path,
    operation: str,
) -> NoReturn:
    """Raise StateError when something exists at the path, but it is not a regular file.

    Args:
        path: The offending path.
        operation: A single lowercase word naming the operation ("read", "hash", ...).
    """

    # 1. Raise structured StateError wrapping an IsADirectoryError
    raise StateError(
        error_name=f"FILE_{operation.upper()}_NOT_A_FILE",
        label=f"path '{path}'",
        value=str(path),
        problem=(
            f"Cannot {operation} '{path}'.",
            "Expected a regular file, but a directory or another kind of entry was found.",
        ),
        expected="A path pointing to a regular file.",
        how_to_fix=(
            "Provide the path of a file, not of a directory.",
            "To work with a directory, use the functions of simplibs-path.",
        ),
        exception=IsADirectoryError,
    )


_DESIGN_NOTES = """
# raise_not_a_file_error — Something Is There, but Not a File

## Purpose
Counterpart of `raise_file_not_found_error`: the path exists, but it is a
directory (or a socket, a device...).

## Exception Base
`IsADirectoryError` is the nearest stdlib type and by far the commonest case.
"""
