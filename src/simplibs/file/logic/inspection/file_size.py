from simplibs.path import PathLike
from simplibs.validate import validate_call
# Outers
from .._common.helpers import resolve_source_file
from .._common.validations import raise_file_access_error


@validate_call
def file_size(
    path: PathLike,
) -> int:
    """Get the size of a file in bytes.

    Args:
        path: The file to measure (a symlink is followed).

    Returns:
        The size in bytes (`0` for an empty file).

    Raises:
        NotFoundError: If the file does not exist.
        StateError: If the path is not a regular file.
        AccessError: If the OS refuses to report the size.
    """

    # 1. Normalize and verify there is a regular file
    source = resolve_source_file(path, "inspect")

    # 2. Ask the OS; no content is read
    try:
        return source.stat().st_size
    except OSError as caught_exc:
        raise_file_access_error(source, "inspect", caught_exc)


_DESIGN_NOTES = """
# file_size — Bytes on Disk, Without Reading Them

## Purpose
A pipeline step ("skip files over 1 MB") and the number behind the `SizeIs`
rule. One `stat`, no content read.

## Strict, Unlike a Predicate
A missing file is an error here (`NotFoundError`), because "size of nothing"
has no honest number. Predicates that must not raise are `is_text_file` and the rules.

## Size, Not Disk Usage
The logical length of the content, as `ls -l` shows it. Sparse files and
compression make the space actually used differ.
"""
