from simplibs.path import PathLike
from simplibs.validate import validate_call
# Outers
from .._common.helpers import resolve_source_file
from .._common.validations import raise_file_access_error


@validate_call
def read_bytes(
    path: PathLike,
) -> bytes:
    """Read the full binary content of a file — the core every other reader is built on.

    Args:
        path: The file to read (a symlink is followed).

    Returns:
        The file's raw bytes.

    Raises:
        NotFoundError: If the file does not exist.
        StateError: If the path is not a regular file.
        AccessError: If the OS refuses the read.
    """

    # 1. Normalize and verify there is a regular file
    source = resolve_source_file(path, "read")

    # 2. Read everything; an OS refusal becomes a card
    try:
        return source.read_bytes()
    except OSError as caught_exc:
        raise_file_access_error(source, "read", caught_exc)


_DESIGN_NOTES = """
# read_bytes — the Core Reader

## Purpose
Every text reader reads bytes here and decodes in memory afterwards.

## Changed From the Old Version
Type and existence checks come from `resolve_source_file`; the read itself
is guarded (a locked file or a permission problem is an `AccessError` card,
not a bare `PermissionError`).

## TODO(test)
Locked file on Windows; a file that vanishes between the check and the read.
"""
