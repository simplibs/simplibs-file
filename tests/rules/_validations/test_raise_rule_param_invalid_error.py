import pytest
from simplibs.exception.testing import assert_exception_function
from simplibs.exception import ParamError
from simplibs.file.rules._validations import raise_rule_param_invalid_error


@pytest.mark.parametrize(
    "rule_name, param_name, value, expected_text, wrapped",
    [
        ("SizeIs", "rule", 42, "a Rule instance", TypeError),
        ("ContentIs", "max_bytes", -1, "a positive int (number of bytes)", ValueError),
        ("IsTextFile", "encoding", "rot13", "a text encoding name", ValueError),
    ],
)
def test_raise_rule_param_invalid_error_contract(
    subtests, rule_name, param_name, value, expected_text, wrapped,
) -> None:
    """Verify raise_rule_param_invalid_error produces a well-formed ParamError card."""

    def raising_wrapper(rejected):
        raise_rule_param_invalid_error(
            rule_name, param_name, rejected, expected_text, exception=wrapped,
        )

    exc = assert_exception_function(
        subtests,
        raising_wrapper,
        invalid_params=(value,),
        exception_type=ParamError,
        error_name="RULE_PARAM_INVALID",
        label=f"{rule_name} parameter '{param_name}'",
        value=value,
        problem=f"Invalid value {value!r} for parameter '{param_name}' of {rule_name}.",
        expected=expected_text,
        how_to_fix=f"Pass {expected_text} as '{param_name}'.",
        exception=wrapped,
        verbose=False,
    )

    # The wrapped stdlib type decides what a caller can catch
    assert isinstance(exc, wrapped)


def test_raise_rule_param_invalid_error_default_exception(subtests) -> None:
    """Without the exception argument the card wraps ValueError."""

    def raising_wrapper(rejected):
        raise_rule_param_invalid_error("SizeIs", "rule", rejected, "a Rule instance")

    exc = assert_exception_function(
        subtests,
        raising_wrapper,
        invalid_params=("bad",),
        exception_type=ParamError,
        error_name="RULE_PARAM_INVALID",
        exception=ValueError,
        verbose=False,
    )

    assert isinstance(exc, ValueError)
