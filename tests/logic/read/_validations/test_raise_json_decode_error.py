import json
from pathlib import Path
import pytest
from simplibs.exception.testing import assert_exception_function
from simplibs.exception import ConversionError
from simplibs.file.logic.read._validations import raise_json_decode_error


def _json_error(source: str) -> json.JSONDecodeError:
    """Produce a real JSONDecodeError for the given source text."""
    try:
        json.loads(source)
    except json.JSONDecodeError as err:
        return err
    raise AssertionError(f"{source!r} unexpectedly parsed as JSON")


@pytest.mark.parametrize("path", [Path("settings.json"), Path("data/payload.json")])
@pytest.mark.parametrize("source", ["{bad", "[1, 2", "", '{"a": }', '{\n  "a": 1,\n}'])
def test_raise_json_decode_error_contract(subtests, source, path) -> None:
    """Verify raise_json_decode_error produces a well-formed ConversionError card with a position."""
    caught_exc = _json_error(source)

    def raising_wrapper(target_path):
        raise_json_decode_error(target_path, caught_exc)

    exc = assert_exception_function(
        subtests,
        raising_wrapper,
        invalid_params=(path,),
        exception_type=ConversionError,
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
        verbose=False,
    )

    # The card must be catchable as the stdlib type it wraps
    assert isinstance(exc, json.JSONDecodeError)
