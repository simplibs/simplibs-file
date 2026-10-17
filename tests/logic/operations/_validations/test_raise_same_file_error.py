from pathlib import Path
import pytest
from simplibs.exception.testing import assert_exception_function
from simplibs.exception import ParamError
from simplibs.file.logic.operations._validations import raise_same_file_error


@pytest.mark.parametrize("operation", ["copy", "move", "backup"])
@pytest.mark.parametrize("path", [Path("data/file.txt"), Path("same.log")])
def test_raise_same_file_error_contract(subtests, path, operation) -> None:
    """Verify raise_same_file_error produces a well-formed ParamError card."""

    def raising_wrapper(target_path):
        raise_same_file_error(target_path, operation)

    exc = assert_exception_function(
        subtests,
        raising_wrapper,
        invalid_params=(path,),
        exception_type=ParamError,
        error_name=f"FILE_{operation.upper()}_SAME_FILE",
        label="destination",
        value=str(path),
        problem=f"Source and destination of the {operation} are the same file: '{path}'.",
        expected="A destination different from the source.",
        how_to_fix=(
            "Choose another destination path.",
            "Check whether a symlink makes two different-looking paths point to one file.",
        ),
        exception=ValueError,
        verbose=False,
    )

    # The card must be catchable as the stdlib type it wraps
    assert isinstance(exc, ValueError)
