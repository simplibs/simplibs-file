from collections.abc import Iterator
from simplibs.path import PathLike
from simplibs.validate import validate_call
# Outers
from ...annotations import EncodingErrors, EncodingName
from .._common.helpers import resolve_source_file
# Inners
from ._helpers import stream_lines


@validate_call
def iter_lines(
    path: PathLike,
    *,
    encoding: EncodingName = "utf-8-sig",
    errors: EncodingErrors = "strict",
    keep_ends: bool = False,
) -> Iterator[str]:
    """Iterate over the lines of a file lazily, without loading it whole.

    The lazy counterpart of `read_lines` — same line rules, same results.
    The path is verified when this function is CALLED; the file is opened
    and decoded while you iterate.

    Args:
        path: The file to read.
        encoding: The text encoding. Defaults to `"utf-8-sig"`.
        errors: How to treat bytes the encoding cannot decode.
        keep_ends: If True, every line keeps its ORIGINAL line ending.

    Returns:
        An iterator of lines. Close it (or exhaust it) to release the file.

    Raises:
        NotFoundError, StateError: At the call, if the path is not a regular file.
        ConversionError, AccessError: During iteration, when that part of the file is reached
            (decoding works in blocks of about 8 KB, so an invalid byte can be reported
            slightly before its own line).
    """

    # 1. Fail early — a missing file is reported here, not at the first next()
    source = resolve_source_file(path, "read")

    # 2. Hand back the lazy stream
    return stream_lines(source, encoding=encoding, errors=errors, keep_ends=keep_ends)


_DESIGN_NOTES = """
# iter_lines — Large Files, One Line at a Time

## Purpose
Memory use stays flat for files of any size — the reader of a multi-gigabyte
log, or an extractor scanning source files.

## Errors: Eager and Lazy
Everything knowable up front (missing, not a file) is raised at the call, like
`iter_paths`. What only the content can reveal (invalid bytes, an OS failure
mid-file) is raised during iteration.

## No Action
A generator does not fit the one-value-in, one-value-out model of an `Action`
(same reasoning as `iter_paths`).
"""
