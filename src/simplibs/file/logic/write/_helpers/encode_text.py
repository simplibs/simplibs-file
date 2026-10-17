import os
from pathlib import Path
# Outers
from ....annotations import EncodingErrors, EncodingName, NewlineMode
from .._validations import raise_encode_error


def encode_text(
    text: str,
    target: Path,
    *,
    encoding: EncodingName = "utf-8",
    errors: EncodingErrors = "strict",
    newline: NewlineMode = "\n",
) -> bytes:
    """Turn text into bytes in memory — line endings first, then the encoding.

    Args:
        text: The text to encode.
        target: The file the bytes are destined for (only used in the failure card).
        encoding: The text encoding to use.
        errors: How to treat characters the encoding cannot represent.
        newline: The line ending that replaces every `"\\n"` in the text
            (`None` for the platform's own).

    Returns:
        The encoded bytes, ready for `write_bytes` / `append_bytes`.

    Raises:
        ConversionError: If a character cannot be encoded (with `errors="strict"`).
    """

    # 1. Resolve the line ending — None means the platform's own
    line_ending = os.linesep if newline is None else newline

    # 2. Translate line ends (the same rule as `open(newline=...)`)
    if line_ending != "\n":
        text = text.replace("\n", line_ending)

    # 3. Encode in memory — the disk has not been touched yet
    try:
        return text.encode(encoding, errors)

    # 4. A character the encoding cannot hold
    except UnicodeEncodeError as caught_exc:
        raise_encode_error(target, encoding, caught_exc)


_DESIGN_NOTES = """
# encode_text — Text to Bytes, Before the Disk

## Purpose
The first half of every text write. All text writers (`write_text`,
`append_text`, `write_lines`, `write_aggregated`, `write_json`) encode here
and then hand BYTES to the two core writers. This fixes the old
`UnicodeEncodeError` that left a truncated file behind, and it is why a bad
character leaves the target completely untouched.

## Plain Function, No `@validate_call`
Internal helper — its callers are already validated.
"""
