from pathlib import Path


def drop_redundant_bom(
    data: bytes,
    target: Path,
    encoding: str,
) -> bytes:
    """Remove a byte-order mark from freshly encoded text that is about to be appended.

    Args:
        data: The encoded bytes (as returned by `encode_text`).
        target: The file the bytes will be appended to.
        encoding: The encoding that produced `data`.

    Returns:
        `data` without its leading preamble when the target already has
        content; `data` unchanged otherwise (a new or empty file keeps its BOM).
    """

    # 1. What does this codec put in front of every encoded chunk? (empty for most; a BOM for utf-8-sig, utf-16, utf-32)
    preamble = "".encode(encoding)
    if not preamble or not data.startswith(preamble):
        return data

    # 2. Is there already something in the file the BOM would land in the middle of?
    try:
        has_content = target.is_file() and target.stat().st_size > 0
    except OSError:
        return data

    # 3. Strip it only when appending to existing content
    return data[len(preamble):] if has_content else data


_DESIGN_NOTES = """
# drop_redundant_bom — One BOM per File, Not per Append

## Purpose
`"utf-8-sig"`, `"utf-16"` and `"utf-32"` emit a BOM on EVERY `encode` call.
`append_text("a")` then `append_text("b")` would leave a BOM in the middle of
the file. This strips it when the file already has content.

## How the Preamble Is Found
`"".encode(encoding)` is exactly what the codec writes in front of any chunk:
b"" for ordinary encodings, the BOM for the BOM codecs. No hard-coded list of
codec names.

## Why Not Needed in `SafeFileWriter`
Its text handle is a real `TextIOWrapper`, which knows it appends to a
non-empty file and writes no second BOM. Only the bytes-based path needs this.
"""
