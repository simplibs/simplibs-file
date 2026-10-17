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


def _caught(factory) -> Exception:
    """Produce the real exception json.dumps raises for the given failing call."""
    try:
        factory()
    except (TypeError, ValueError) as err:
        return err
    raise AssertionError("the call unexpectedly succeeded")


_FAILURES = {
    "unserializable_type": lambda: json.dumps(object()),
    "circular_reference": _circular,
    "nan_not_allowed": lambda: json.dumps(float("nan"), allow_nan=False),
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
            "Remove circular references and NaN/infinity values.",
        ),
        exception=type(caught_exc),
        verbose=False,
    )

    # TypeError and ValueError must both survive as the catchable type
    assert isinstance(exc, type(caught_exc))
