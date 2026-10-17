from pathlib import Path
from simplibs.path import PathLike, normalize_path
from simplibs.validate import validate_call
# Outers
from ...annotations import EncodingErrors, EncodingName, NewlineMode
# Inners
from .write_bytes import write_bytes
from ._helpers import encode_text


@validate_call
def write_text(
    path: PathLike,
    text: str,
    *,
    encoding: EncodingName = "utf-8",
    errors: EncodingErrors = "strict",
    newline: NewlineMode = "\n",
    overwrite: bool = True,
    use_draft: bool = True,
    sync: bool = False,
) -> Path:
    """Write text to a file.

    The text is encoded in memory first, so an unencodable character fails
    before the disk is touched.

    Args:
        path: The target file. Its folder is created if missing.
        text: The text to write.
        encoding: The text encoding. Defaults to `"utf-8"` (no BOM).
        errors: How to treat characters the encoding cannot hold.
        newline: The line ending written for every `"\\n"` (`None` for the platform's own).
        overwrite: If False, an existing file raises instead of being replaced.
        use_draft: Atomic draft-and-swap write (default) or an in-place write.
        sync: Force the data to stable storage.

    Returns:
        The normalized target `Path`.

    Raises:
        ConversionError: If a character cannot be encoded.
        StateError, AlreadyExistsError, AccessError: As for `write_bytes`.
    """

    # 1. Normalize once — the encoder needs the path for its failure card
    target = normalize_path(path)

    # 2. Encode in memory; the file is untouched if this fails
    data = encode_text(text, target, encoding=encoding, errors=errors, newline=newline)

    # 3. Hand the bytes to the core writer
    return write_bytes(target, data, overwrite=overwrite, use_draft=use_draft, sync=sync)


_DESIGN_NOTES = """
# write_text — Encode, Then Write

## Purpose
The text face of `write_bytes`. Three old defects are gone because of the
"encode first" order:
* `Path.write_text` truncated the file BEFORE encoding, so a `UnicodeEncodeError`
  left a truncated file;
* `UnicodeEncodeError` is a `ValueError`, so the old `except OSError` never saw it;
* the platform decided the line ending (`\\r\\n` on Windows).

## Defaults
`utf-8` without BOM, `"\\n"` line endings. Anything else is an explicit choice.

## BOM Codecs
`encoding="utf-8-sig"` writes the BOM at the start of the new file — which is
what that encoding means.
"""
