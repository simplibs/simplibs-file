from collections.abc import Collection
from pathlib import Path
from simplibs.path import PathLike
from simplibs.validate import validate_call
# Outers
from ...annotations import EncodingErrors, EncodingName, NewlineMode
# Inners
from .write_text import write_text


@validate_call
def write_lines(
    path: PathLike,
    lines: Collection[str],
    *,
    encoding: EncodingName = "utf-8",
    errors: EncodingErrors = "strict",
    newline: NewlineMode = "\n",
    trailing_newline: bool = True,
    overwrite: bool = True,
    use_draft: bool = True,
    sync: bool = False,
) -> Path:
    """Write a collection of lines to a file, one per line.

    The counterpart of `read_lines`. Each item is written WITHOUT its own line
    ending — pass lines as `read_lines` returns them by default.

    Args:
        path: The target file. Its folder is created if missing.
        lines: The lines, in order.
        encoding: The text encoding.
        errors: How to treat characters the encoding cannot hold.
        newline: The line ending placed between lines (`None` for the platform's own).
        trailing_newline: If True (default), the last line is also terminated,
            as POSIX tools expect. An empty collection always gives an empty file.
        overwrite: If False, an existing file raises instead of being replaced.
        use_draft: Atomic draft-and-swap write (default) or an in-place write.
        sync: Force the data to stable storage.

    Returns:
        The normalized target `Path`.
    """

    # 1. Join the lines with "\n" — `write_text` translates it to the chosen line ending
    text = "\n".join(lines)

    # 2. Terminate the last line, but never turn an empty collection into a lone newline
    if trailing_newline and lines:
        text += "\n"

    # 3. Write it
    return write_text(
        path,
        text,
        encoding=encoding,
        errors=errors,
        newline=newline,
        overwrite=overwrite,
        use_draft=use_draft,
        sync=sync,
    )


_DESIGN_NOTES = """
# write_lines — the Symmetry of `read_lines`

## Purpose
`write_lines(p, read_lines(p))` reproduces a file (with `keep_ends=False`,
the default of `read_lines`). A thin function over `write_text`.

## Lines Carry No Line Ending
An item that already ends with `"\\n"` is written as is, so the file would get
an empty line after it. Items from `read_lines(keep_ends=True)` should be
written with `write_text("".join(...))` instead.

## `trailing_newline=True`
A text file conventionally ends with a line ending. `False` gives the exact
`"\\n".join(lines)`.

## `Collection`, Not `Iterable`
The lines are used twice (join + emptiness test) and `@validate_call` must be
able to inspect them without consuming a generator.

## TODO(test)
* Empty collection with `trailing_newline=True` -> empty file.
* Items containing `"\\n"` -> more lines than items (documented).
* Round trip with `read_lines`.
"""
