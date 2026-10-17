from collections.abc import Iterator
from pathlib import Path
# Outers
from ..._common.validations import raise_file_access_error
from .._validations import raise_decode_error
# Inners
from .strip_line_ending import strip_line_ending


def stream_lines(
    source: Path,
    *,
    encoding: str,
    errors: str,
    keep_ends: bool,
) -> Iterator[str]:
    """Yield the lines of a verified file one at a time, never holding the whole file.

    Args:
        source: A normalized path that `resolve_source_file` already accepted.
        encoding: The text encoding.
        errors: How to treat undecodable bytes.
        keep_ends: Whether each line keeps its original line ending.

    Yields:
        The lines, in order; `\\n`, `\\r\\n` and `\\r` end a line, nothing else does.
    """

    # 1. Open lazily; newline="" keeps the original endings and recognizes all three
    try:
        with source.open("r", encoding=encoding, errors=errors, newline="") as handle:

            # 2. One line at a time
            for line in handle:
                yield line if keep_ends else strip_line_ending(line)

    # 3. Invalid bytes surface when that part of the file is reached
    except UnicodeDecodeError as caught_exc:
        raise_decode_error(source, encoding, caught_exc, offset_known=False)

    # 4. An OS failure in the middle of the file
    except OSError as caught_exc:
        raise_file_access_error(source, "read", caught_exc)


_DESIGN_NOTES = """
# stream_lines — the Generator Behind `iter_lines`

## Why a Separate Function
`iter_lines` must report a missing file at the CALL, not at the first
`next()`. A function containing `yield` is a generator and runs nothing until
iterated, so the eager checks live in `iter_lines` and only the streaming
lives here.

## Decoding Works in Blocks
The text layer decodes about 8 KB at a time, so an invalid byte can be
reported while the lines BEFORE it in the same block are not yet yielded. The
error never appears for a block that is never reached. The card omits the byte
offset (it would be relative to the block).

## TODO(test)
* Closing the generator early closes the file.
* Invalid bytes far beyond the first block: earlier lines are yielded first.
"""
