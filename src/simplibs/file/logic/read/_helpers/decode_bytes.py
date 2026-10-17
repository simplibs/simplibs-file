from pathlib import Path
# Outers
from ....annotations import EncodingErrors, EncodingName
from .._validations import raise_decode_error


def decode_bytes(
    data: bytes,
    source: Path,
    *,
    encoding: EncodingName = "utf-8-sig",
    errors: EncodingErrors = "strict",
) -> str:
    """Turn bytes into text in memory.

    Args:
        data: The bytes read from a file.
        source: The file the bytes came from (only used in the failure card).
        encoding: The text encoding. `"utf-8-sig"` also accepts files without a BOM.
        errors: How to treat bytes the encoding cannot decode.

    Returns:
        The decoded text, line endings untouched.

    Raises:
        ConversionError: If the bytes are not valid text (with `errors="strict"`).
    """

    # 1. Decode in memory
    try:
        return data.decode(encoding, errors)

    # 2. Invalid bytes — a card with the offset instead of a bare UnicodeDecodeError
    except UnicodeDecodeError as caught_exc:
        raise_decode_error(source, encoding, caught_exc)


_DESIGN_NOTES = """
# decode_bytes — Bytes to Text, After the Disk

## Purpose
The mirror of `encode_text`: every text reader reads BYTES first
(`read_bytes`) and decodes here, so decoding exists once and
`UnicodeDecodeError` (a `ValueError`, invisible to `except OSError`) becomes a
card everywhere.

## Why `utf-8-sig` Is the Default of Reads
Files saved by Windows tools often start with a BOM; plain `utf-8` would keep
it as a stray `\\ufeff` and make `json.loads` fail. `utf-8-sig` strips a BOM
if present and accepts files without one. Writes stay BOM-free `utf-8`.
"""
