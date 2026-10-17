from pathlib import Path
from typing import NoReturn
from simplibs.exception import ConversionError


def raise_decode_error(
    path: Path,
    encoding: str,
    caught_exc: UnicodeDecodeError,
    *,
    offset_known: bool = True,
) -> NoReturn:
    """Raise ConversionError when a file's bytes are not valid text in the given encoding.

    Args:
        path: The file being read.
        encoding: The encoding the file was decoded with.
        caught_exc: The `UnicodeDecodeError` that was caught.
        offset_known: False when the error came from a streamed read, where
            the offset inside the exception is relative to a block, not to the file.
    """

    # 1. Say where only when the position is a real position in the file
    where = (
        f"Invalid data at byte offset {caught_exc.start}: {caught_exc.reason}."
        if offset_known
        else f"Invalid data found while reading the file: {caught_exc.reason}."
    )

    # 2. Raise structured ConversionError wrapping the UnicodeDecodeError
    raise ConversionError(
        error_name="FILE_DECODE_FAILED",
        label=f"file '{path}'",
        value=str(path),
        problem=(
            f"Cannot decode '{path}' as {encoding!r}.",
            where,
        ),
        expected=f"Content that is valid {encoding!r} text.",
        how_to_fix=(
            "Pass the encoding the file was really written in (e.g. encoding='cp1250' or 'latin-1').",
            "Use errors='replace' to read it with substitution characters instead of failing.",
            "If the file is binary, read it with read_bytes().",
        ),
        exception=UnicodeDecodeError,
    )


_DESIGN_NOTES = """
# raise_decode_error — Bytes That Are Not Text

## Purpose
`UnicodeDecodeError` is a `ValueError`, so the old `except OSError` never
caught it and a bare traceback leaked. The card names the encoding and the
byte offset where decoding stopped.

## `offset_known`
A streamed read (`iter_lines`) decodes in blocks, so the offset inside the
exception is relative to the block. The card then omits the number instead of
printing a wrong one.
"""
