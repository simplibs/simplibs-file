import json
from typing import Any
from simplibs.path import PathLike, normalize_path
from simplibs.validate import validate_call
# Outers
from ...annotations import EncodingErrors, EncodingName
# Inners
from .read_text import read_text
from ._validations import raise_json_decode_error


@validate_call
def read_json(
    path: PathLike,
    *,
    encoding: EncodingName = "utf-8-sig",
    errors: EncodingErrors = "strict",
) -> Any:
    """Read a file and parse its content as JSON.

    Args:
        path: The JSON file to read.
        encoding: The text encoding. Defaults to `"utf-8-sig"`, so a BOM
            written by a Windows tool does not break parsing.
        errors: How to treat bytes the encoding cannot decode.

    Returns:
        The parsed value (dict, list, str, int, float, bool or None).

    Raises:
        NotFoundError, StateError, AccessError: As for `read_bytes`.
        ConversionError: If the bytes are not valid text, or the text is not valid JSON.
    """

    # 1. Normalize once — the failure card needs the path
    source = normalize_path(path)

    # 2. Read and decode (BOM-tolerant)
    text = read_text(source, encoding=encoding, errors=errors)

    # 3. Parse; a syntax error becomes a card with line and column
    try:
        return json.loads(text)
    except json.JSONDecodeError as caught_exc:
        raise_json_decode_error(source, caught_exc)


_DESIGN_NOTES = """
# read_json — Parse, With a Position

## Changed From the Old Version
* BOM-tolerant: `json.load` on a plain `utf-8` handle fails with
  "Unexpected UTF-8 BOM" on files saved by many Windows tools.
* The path must be a regular file (the old version only checked existence, so a
  directory raised a raw `IsADirectoryError`).
* Undecodable bytes and OS failures are cards, not bare exceptions.
* The syntax error carries line and column.

## Whole Document in Memory
Large JSON is not streamed; that is outside this library's scope.

## TODO(test)
BOM present; empty file (-> `JSONDecodeError` card); directory; invalid UTF-8; `NaN` is accepted by `json.loads` (as in the standard library).
"""
