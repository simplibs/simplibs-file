from pathlib import Path
import pytest
from simplibs.exception.testing import assert_exception_function
from simplibs.exception import AlreadyExistsError
from simplibs.file.logic._common.validations import raise_destination_exists_error


@pytest.mark.parametrize("operation", ["copy", "move", "write"])
@pytest.mark.parametrize("path", [Path("out/report.txt"), Path("data.json")])
def test_raise_destination_exists_error_contract(subtests, path, operation) -> None:
    """Verify raise_destination_exists_error produces a well-formed AlreadyExistsError card."""

    def raising_wrapper(target_path):
        raise_destination_exists_error(target_path, operation)

    exc = assert_exception_function(
        subtests,
        raising_wrapper,
        invalid_params=(path,),
        exception_type=AlreadyExistsError,
        error_name=f"FILE_{operation.upper()}_DESTINATION_EXISTS",
        label=f"destination '{path}'",
        value=str(path),
        problem=(
            f"Cannot {operation} onto '{path}'.",
            "The destination already exists and overwriting is not allowed.",
        ),
        expected="A destination path that does not exist yet, or overwrite=True.",
        how_to_fix=(
            "Pass overwrite=True if replacing the existing file is intended.",
            "Choose a different destination, or use make_unique_path() from simplibs-path.",
        ),
        exception=FileExistsError,
        verbose=False,
    )

    # The card must be catchable as the stdlib type it wraps
    assert isinstance(exc, FileExistsError)
