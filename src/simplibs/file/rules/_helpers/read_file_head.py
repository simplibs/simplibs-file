import codecs
from pathlib import Path


def read_file_head(
    path: Path,
    *,
    max_bytes: int,
    encoding: str,
) -> str | None:
    """Read and decode the beginning of a regular file without raising.

    Args:
        path: The file to read.
        max_bytes: How many bytes from the start to read.
        encoding: The text encoding to decode with.

    Returns:
        The decoded text with line endings normalized to `"\\n"` (an empty file
        gives `""`), or `None` if the path is not a regular file, cannot be
        read, or the bytes do not decode.
    """

    # 1. Read only the beginning
    try:
        if not path.is_file():
            return None
        with path.open("rb") as handle:
            data = handle.read(max_bytes)
    except (OSError, ValueError):
        return None

    # 2. Decode incrementally: a multi-byte character cut by the end of the head is no error —
    #    unless the head is the whole file
    decoder = codecs.getincrementaldecoder(encoding)(errors="strict")
    try:
        text = decoder.decode(data, final=len(data) < max_bytes)
    except UnicodeDecodeError:
        return None

    # 3. The same newline normalization as `read_text`
    return text.replace("\r\n", "\n").replace("\r", "\n")


_DESIGN_NOTES = """
# read_file_head — Just Enough of a File to Judge It

## Purpose
`ContentIs` asks questions like "starts with a shebang" or "mentions TODO in
its first lines". Reading a whole large file for that would make a scan slow.

## Same Decoding Rules as `is_text_file`
Incremental decoder, `final` only when the head is the whole file, so a
character cut at `max_bytes` is not mistaken for corruption.

## `""` Is a Valid Answer
An empty file has empty content; only `None` means "could not be read".
"""
