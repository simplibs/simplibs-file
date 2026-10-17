import json
from pathlib import Path
import pytest
from simplibs.exception.testing import assert_exception_function
from simplibs.exception import ConversionError
from simplibs.file.logic.write._validations import raise_json_encode_error


def _circular() -> str:
    """Serialize a list that contains itself."""
    data: list = []
    data.append(data)
    return json.dumps(data)


# Deeper than the recursion limit of every supported Python (3.12+ counts C recursion separately)
_DEPTH = 100_000


def _too_deep() -> str:
    """Serialize a list nested far deeper than the interpreter's recursion limit."""
    data: list = []
    for _ in range(_DEPTH):
        data = [data]
    return json.dumps(data)


def _caught(factory) -> Exception:
    """Produce the real exception json.dumps raises for the given failing call."""
    try:
        factory()
    except (TypeError, ValueError, RecursionError) as err:
        return err
    raise AssertionError("the call unexpectedly succeeded")


_FAILURES = {
    "unserializable_type": lambda: json.dumps(object()),
    "circular_reference": _circular,
    "nan_not_allowed": lambda: json.dumps(float("nan"), allow_nan=False),
    "nesting_too_deep": _too_deep,
}


@pytest.mark.parametrize("path", [Path("out.json"), Path("data/payload.json")])
@pytest.mark.parametrize("factory", list(_FAILURES.values()), ids=list(_FAILURES.keys()))
def test_raise_json_encode_error_contract(subtests, factory, path) -> None:
    """Verify raise_json_encode_error produces a well-formed ConversionError card."""
    caught_exc = _caught(factory)

    def raising_wrapper(target_path):
        raise_json_encode_error(target_path, caught_exc)

    exc = assert_exception_function(
        subtests,
        raising_wrapper,
        invalid_params=(path,),
        exception_type=ConversionError,
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
        verbose=False,
    )

    # TypeError and ValueError must both survive as the catchable type
    assert isinstance(exc, type(caught_exc))
