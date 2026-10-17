import json
from collections.abc import Callable
from pathlib import Path
from typing import Any
from simplibs.path import PathLike, normalize_path
from simplibs.validate import validate_call
# Outers
from ...annotations import EncodingName, NewlineMode
# Inners
from .write_text import write_text
from ._validations import raise_json_encode_error


@validate_call
def write_json(
    path: PathLike,
    data: Any,
    *,
    indent: int | str | None = 2,
    ensure_ascii: bool = False,
    sort_keys: bool = False,
    allow_nan: bool = False,
    default: Callable[[Any], Any] | None = None,
    trailing_newline: bool = True,
    encoding: EncodingName = "utf-8",
    newline: NewlineMode = "\n",
    overwrite: bool = True,
    use_draft: bool = True,
    sync: bool = False,
) -> Path:
    """Serialize a value to JSON and write it to a file.

    The value is serialized in memory first, so an unserializable value fails
    before the disk is touched.

    Args:
        path: The target file. Its folder is created if missing.
        data: The JSON-serializable value.
        indent: Indentation (an `int` of spaces or a string); `None` for compact output.
        ensure_ascii: If False (default), non-ASCII characters are written as they are
            (`č`, not `\\u010d`).
        sort_keys: If True, object keys are sorted — reproducible output.
        allow_nan: If False (default), `NaN`/`Infinity` are refused, because
            they are not valid JSON.
        default: A function converting objects JSON cannot serialize to
            something it can (called like `json.dumps(default=...)`).
        trailing_newline: If True (default), the file ends with a line ending.
        encoding: The text encoding. Defaults to `"utf-8"`.
        newline: The line ending written for every `"\\n"` (`None` for the platform's own).
        overwrite: If False, an existing file raises instead of being replaced.
        use_draft: Atomic draft-and-swap write (default) or an in-place write.
        sync: Force the data to stable storage.

    Returns:
        The normalized target `Path`.

    Raises:
        ConversionError: If the value cannot be serialized or encoded.
        StateError, AlreadyExistsError, AccessError: As for `write_bytes`.
    """

    # 1. Normalize once — the failure card needs the path
    target = normalize_path(path)

    # 2. Serialize in memory; the file is untouched if this fails
    try:
        text = json.dumps(
            data,
            indent=indent,
            ensure_ascii=ensure_ascii,
            sort_keys=sort_keys,
            allow_nan=allow_nan,
            default=default,
        )
    except (TypeError, ValueError, RecursionError) as caught_exc:
        raise_json_encode_error(target, caught_exc)

    # 3. A text file ends with a line ending
    if trailing_newline:
        text += "\n"

    # 4. Write it
    return write_text(
        target,
        text,
        encoding=encoding,
        newline=newline,
        overwrite=overwrite,
        use_draft=use_draft,
        sync=sync,
    )


_DESIGN_NOTES = """
# write_json — Serialize First, Then Write

## Purpose
The JSON face of `write_text`.

---

## 1. Serialize Into Memory
The old `json.dump(data, handle)` wrote in chunks, so a `TypeError` in the
middle of a large structure left a half-written (invalid) file when
`use_draft=False`. `json.dumps` first means the file is touched only by a
complete document.

## 2. Changed Defaults
* `ensure_ascii=False` — Czech and other text stays readable instead of `\\u010d`.
* `allow_nan=False` — `NaN` is not JSON; most parsers reject it. Fail loudly
  at write time rather than produce a file other tools cannot read.
* `trailing_newline=True` — a text file ends with a line ending.

## 3. New Options
`sort_keys` (reproducible output, clean diffs), `default` (custom types),
`indent` as `int | str`.

## 4. `errors` Is Not Offered
JSON is almost always UTF-8, where nothing is unencodable. For another
encoding an unencodable character is a real error and a `ConversionError`
card is the right answer.
"""
