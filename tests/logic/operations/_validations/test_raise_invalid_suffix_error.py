import pytest
from simplibs.exception.testing import assert_exception_function
from simplibs.exception import ParamError
from simplibs.file.logic.operations._validations import raise_invalid_suffix_error


@pytest.mark.parametrize("operation", ["backup", "copy"])
@pytest.mark.parametrize("suffix", ["bak", ".a/b", ".x\\y"])
def test_raise_invalid_suffix_error_contract(subtests, suffix, operation) -> None:
    """Verify raise_invalid_suffix_error produces a well-formed ParamError card."""

    def raising_wrapper(bad_suffix):
        raise_invalid_suffix_error(bad_suffix, operation)

    exc = assert_exception_function(
        subtests,
        raising_wrapper,
        invalid_params=(suffix,),
        exception_type=ParamError,
        error_name=f"FILE_{operation.upper()}_INVALID_SUFFIX",
        label="suffix",
        value=suffix,
        problem=f"{suffix!r} is not a valid suffix for the {operation}.",
        expected=(
            "An empty string, or a dot followed by at least one character, "
            "without path separators (e.g. '.bak', '.tar.gz')."
        ),
        how_to_fix=(
            "Start the suffix with a dot, e.g. '.bak'.",
            "Do not use '/', '\\' or null characters in it.",
        ),
        exception=ValueError,
        verbose=False,
    )

    # The card must be catchable as the stdlib type it wraps
    assert isinstance(exc, ValueError)
