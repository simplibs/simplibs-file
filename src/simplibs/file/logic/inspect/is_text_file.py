import codecs
from simplibs.exception import SimpleException
from simplibs.path import PathLike, normalize_path
from simplibs.validate import validate_call
# Outers
from ...annotations import ByteCount, EncodingName


@validate_call
def is_text_file(
    path: PathLike,
    *,
    sample_size: ByteCount = 8192,
    encoding: EncodingName = "utf-8",
    _validate_call: bool = True,
) -> bool:
    """Check whether a file looks like text, judging by its first bytes, without raising.

    Args:
        path: The file to check.
        sample_size: How many bytes from the start to inspect.
        encoding: The encoding the text is expected to have.
        _validate_call: Internal bypass switch for `@validate_call` — rules
            pass `False` because they have already checked the input type.

    Returns:
        True for an empty file, or a regular file whose first `sample_size`
        bytes decode in `encoding` and contain no NUL character. False for
        anything else — including a missing path, a directory, an unreadable
        file, undecodable bytes and binary content.
    """

    # 1. Read the sample; any refusal of the OS or of path handling is a plain "no"
    try:
        candidate = normalize_path(path)
        if not candidate.is_file():
            return False
        with candidate.open("rb") as handle:
            sample = handle.read(sample_size)
    except (OSError, ValueError, SimpleException):
        return False

    # 2. An empty file is text by convention (as `file` and Git treat it)
    if not sample:
        return True

    # 3. Decode incrementally: a multi-byte character cut by the end of the sample is not an error —
    #    unless the sample is the whole file
    decoder = codecs.getincrementaldecoder(encoding)(errors="strict")
    try:
        text = decoder.decode(sample, final=len(sample) < sample_size)
    except UnicodeDecodeError:
        return False

    # 4. A NUL character is the classic mark of binary content (a NUL BYTE is fine in UTF-16/32 text)
    return "\x00" not in text


_DESIGN_NOTES = """
# is_text_file — Text or Binary?

## Purpose
The predicate behind the `IsTextFile` rule: "skip images and archives" in an
extraction pipeline, before any decoding is attempted.

## A Heuristic, Honestly
Only the first `sample_size` bytes are judged. A binary file whose first 8 KB
happen to be valid text passes; a text file with a NUL at the 9th kilobyte
passes too. Two cheap, decisive signals: the sample must decode, and must not
contain a NUL character.

## Decode, Don't Count Bytes
A NUL BYTE is normal in UTF-16/UTF-32 text, so searching the bytes would call
such files binary. Searching the DECODED text for `"\\x00"` is correct for every
encoding.

## The Cut Character
The sample ends wherever `sample_size` falls, possibly in the middle of a
multi-byte character. An incremental decoder with `final=False` waits for the
rest; `final=True` is used only when the sample is the whole file.

## Never Raises for Disk Problems
Same contract as `is_path_readable`; a wrong TYPE of argument is still rejected
by the annotations. The `_validate_call` switch lets the rule skip the second validation.

## Empty File
Text (True) — consistent with `file --mime` and Git.

## TODO(test)
UTF-8 text; binary with NUL; UTF-16 with `encoding="utf-16"`; the same file with the default encoding -> False;
a multi-byte character cut at `sample_size`; empty file; directory; missing path; unreadable file; invalid UTF-8
(`cp1250` text) with the default encoding.
"""
