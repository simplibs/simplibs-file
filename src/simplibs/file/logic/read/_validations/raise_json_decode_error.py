import json
from pathlib import Path
from typing import NoReturn
from simplibs.exception import ConversionError


def raise_json_decode_error(
    path: Path,
    caught_exc: json.JSONDecodeError,
) -> NoReturn:
    """Raise ConversionError when a file's content is not valid JSON.

    Args:
        path: The file being read.
        caught_exc: The `json.JSONDecodeError` that was caught.
    """

    # 1. Raise structured ConversionError wrapping the JSONDecodeError
    raise ConversionError(
        error_name="FILE_JSON_DECODE_FAILED",
        label=f"file '{path}'",
        value=str(path),
        problem=(
            f"File '{path}' does not contain valid JSON.",
            f"{caught_exc.msg} (line {caught_exc.lineno}, column {caught_exc.colno}).",
        ),
        expected="A file whose whole content is one valid JSON value.",
        how_to_fix=(
            f"Check the JSON syntax near line {caught_exc.lineno}, column {caught_exc.colno}.",
            "JSON allows no comments, no trailing commas and only double-quoted strings.",
        ),
        exception=json.JSONDecodeError,
    )


_DESIGN_NOTES = """
# raise_json_decode_error — Malformed JSON, With a Position

## Purpose
Replaces `raise_read_json_invalid_error`. Adds the line and column that the
`JSONDecodeError` already knows.
"""
