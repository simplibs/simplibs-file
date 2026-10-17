from pathlib import Path
from typing import NoReturn
from simplibs.exception import ConversionError


def raise_json_encode_error(
    path: Path,
    caught_exc: Exception,
) -> NoReturn:
    """Raise ConversionError when a value cannot be serialized to JSON.

    Args:
        path: The file that was going to be written.
        caught_exc: The `TypeError`, `ValueError` or `RecursionError` raised by `json.dumps`.
    """

    # 1. Raise structured ConversionError wrapping the serialization failure
    raise ConversionError(
        error_name="FILE_JSON_ENCODE_FAILED",
        label=f"data for '{path}'",
        value=str(path),
        problem=(
            f"Cannot serialize the data for '{path}' to JSON.",
            f"{type(caught_exc).__name__}: {caught_exc}",
        ),
        expected="A JSON-compatible value (dict, list, str, int, float, bool or None, nested freely).",
        how_to_fix=(
            "Convert custom objects to plain values, or pass default=... to convert them.",
            "Remove circular references and NaN/infinity values, and flatten extremely deep nesting.",
        ),
        exception=type(caught_exc),
    )


_DESIGN_NOTES = """
# raise_json_encode_error — a Value JSON Cannot Hold

## Purpose
`write_json` serializes into memory first (`json.dumps`), so this card is
raised while the target file is still untouched — the old `json.dump`
straight into the handle could leave a half-written file.

## `TypeError`, `ValueError` and `RecursionError`
Unserializable type -> `TypeError`; circular reference or NaN -> `ValueError`;
nesting deeper than the interpreter's recursion limit -> `RecursionError`.
"""
