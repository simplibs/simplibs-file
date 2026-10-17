import io
from simplibs.path import PathLike, normalize_path
from simplibs.validate import validate_call
# Outers
from ...annotations import EncodingErrors, EncodingName
# Inners
from ._helpers import decode_bytes, strip_line_ending
from .read_bytes import read_bytes


@validate_call
def read_lines(
    path: PathLike,
    *,
    encoding: EncodingName = "utf-8-sig",
    errors: EncodingErrors = "strict",
    keep_ends: bool = False,
) -> list[str]:
    """Read a file as a list of lines.

    Only `"\\n"`, `"\\r\\n"` and `"\\r"` end a line. Form feeds and Unicode
    separators (`\\x0c`, `\\x85`, `\\u2028`...) stay inside their line.

    Args:
        path: The file to read.
        encoding: The text encoding. Defaults to `"utf-8-sig"`.
        errors: How to treat bytes the encoding cannot decode.
        keep_ends: If True, every line keeps its ORIGINAL line ending.

    Returns:
        The lines, in order. An empty file gives `[]`; a final line without
        a terminator is returned as it is.

    Raises:
        NotFoundError, StateError, AccessError: As for `read_bytes`.
        ConversionError: If the bytes are not valid text in the encoding.
    """

    # 1. Normalize once — the decoder needs the path for its failure card
    source = normalize_path(path)

    # 2. Read the bytes, decode them in memory
    text = decode_bytes(read_bytes(source), source, encoding=encoding, errors=errors)

    # 3. Split on \n, \r\n and \r only — newline="" leaves the endings untranslated
    lines = io.StringIO(text, newline="").readlines()

    # 4. Keep or strip the original endings
    return lines if keep_ends else [strip_line_ending(line) for line in lines]


_DESIGN_NOTES = """
# read_lines — Lines the Way a File Defines Them

## Why Not `str.splitlines`
`splitlines()` also splits on `\\x0b`, `\\x0c`, `\\x1c-\\x1e`, `\\x85`, `\\u2028`
and `\\u2029` — a source file containing a form feed would fall apart — and
with `keepends=True` it returned endings that were already translated.
`StringIO(text, newline="")` splits only on real line endings and keeps them
exactly as they were.

## Memory
The whole file is loaded. For large files use `iter_lines`.
"""
