from pathlib import Path
from typing import NoReturn
from simplibs.exception import NotFoundError


def raise_file_not_found_error(
    path: Path,
    operation: str,
) -> NoReturn:
    """Raise NotFoundError when the file an operation needs does not exist.

    Args:
        path: The missing file.
        operation: A single lowercase word naming the operation ("read", "copy", ...).
    """

    # 1. Raise structured NotFoundError wrapping a FileNotFoundError
    raise NotFoundError(
        error_name=f"FILE_{operation.upper()}_NOT_FOUND",
        label=f"file '{path}'",
        value=str(path),
        problem=f"Cannot {operation} '{path}': no such file exists.",
        expected="A path to an existing file.",
        how_to_fix=(
            "Check the spelling of the path and the current working directory.",
            "Make sure the file was created before this step runs.",
        ),
        exception=FileNotFoundError,
    )


_DESIGN_NOTES = """
# raise_file_not_found_error — a Required File Is Missing

## Purpose
One card for every operation that needs an existing file. `operation` only
changes the wording and the `error_name` (`FILE_READ_NOT_FOUND`,
`FILE_COPY_NOT_FOUND`, ...), so ~20 near-identical helpers of the old layout
collapse into one.

## `operation` Is One Word
It is placed into a sentence and upper-cased into the error name.
"""
