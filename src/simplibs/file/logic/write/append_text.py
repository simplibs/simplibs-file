from pathlib import Path
from simplibs.path import PathLike, normalize_path
from simplibs.validate import validate_call
# Outers
from ...annotations import EncodingErrors, EncodingName, NewlineMode
# Inners
from ._helpers import drop_redundant_bom, encode_text
from .append_bytes import append_bytes


@validate_call
def append_text(
    path: PathLike,
    text: str,
    *,
    encoding: EncodingName = "utf-8",
    errors: EncodingErrors = "strict",
    newline: NewlineMode = "\n",
    use_draft: bool = False,
    sync: bool = False,
) -> Path:
    """Append text to a file, creating it if it does not exist.

    Args:
        path: The target file. Its folder is created if missing.
        text: The text to add after the existing content.
        encoding: The text encoding. Should match the file's existing encoding.
        errors: How to treat characters the encoding cannot hold.
        newline: The line ending written for every `"\\n"` (`None` for the platform's own).
        use_draft: Copy-append-swap (all-or-nothing, but the cost grows with
            the file) instead of the default in-place append.
        sync: Force the data to stable storage.

    Returns:
        The normalized target `Path`.

    Raises:
        ConversionError: If a character cannot be encoded.
        StateError, AccessError: As for `append_bytes`.
    """

    # 1. Normalize once — the encoder needs the path for its failure card
    target = normalize_path(path)

    # 2. Encode in memory; the file is untouched if this fails
    data = encode_text(text, target, encoding=encoding, errors=errors, newline=newline)

    # 3. A BOM belongs at the start of a file, never in the middle
    data = drop_redundant_bom(data, target, encoding)

    # 4. Hand the bytes to the core appender
    return append_bytes(target, data, use_draft=use_draft, sync=sync)


_DESIGN_NOTES = """
# append_text — Encode, Strip the BOM, Append

## Purpose
The text face of `append_bytes`.

## `use_draft=False` by Default
Changed from the old `True`: a draft append copies the whole existing file on
every call. Documented in the parameter; opt in with `use_draft=True`.

## BOM Handling
`drop_redundant_bom` removes the BOM that `utf-8-sig` / `utf-16` / `utf-32`
add on every encode, when the file already has content.

## The Caller Owns Encoding Consistency
Appending `cp1250` text to a `utf-8` file produces a mixed file; the library
cannot tell what is already in it.

## TODO(test)
* Two appends with `utf-8-sig` -> exactly one BOM.
* Unencodable character -> `ConversionError`, file untouched.
* Append to a missing file creates it (with BOM for the BOM codecs).
"""
