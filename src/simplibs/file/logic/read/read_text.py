from simplibs.path import PathLike, normalize_path
from simplibs.validate import validate_call
# Outers
from ...annotations import EncodingErrors, EncodingName
# Inners
from .read_bytes import read_bytes
from ._helpers import decode_bytes


@validate_call
def read_text(
    path: PathLike,
    *,
    encoding: EncodingName = "utf-8-sig",
    errors: EncodingErrors = "strict",
) -> str:
    """Read the full text of a file.

    Line endings are normalized to `"\\n"` (as Python's own text mode does). Use
    `read_lines` to keep the original endings.

    Args:
        path: The file to read.
        encoding: The text encoding. Defaults to `"utf-8-sig"` — a BOM is
            removed if present and files without one are fine.
        errors: How to treat bytes the encoding cannot decode.

    Returns:
        The decoded text.

    Raises:
        NotFoundError, StateError, AccessError: As for `read_bytes`.
        ConversionError: If the bytes are not valid text in the encoding.
    """

    # 1. Normalize once — the decoder needs the path for its failure card
    source = normalize_path(path)

    # 2. Read the bytes, decode them in memory
    text = decode_bytes(read_bytes(source), source, encoding=encoding, errors=errors)

    # 3. Universal newlines — "\r\n" first, or it would become two line ends
    return text.replace("\r\n", "\n").replace("\r", "\n")


_DESIGN_NOTES = """
# read_text — the Whole File as Text

## Defaults
`utf-8-sig` for reading (BOM tolerant), `strict` errors. The write side stays
`utf-8` without BOM.

## Newlines
`"\\r\\n"` and lone `"\\r"` become `"\\n"` — the same result as `Path.read_text`,
so code that moves from `pathlib` keeps behaving. A caller who needs the exact
bytes of the line endings uses `read_lines(keep_ends=True)` or `read_bytes`.
"""
