from pathlib import Path
import pytest
from simplibs.exception.testing import assert_exception_function
from simplibs.exception import StateError
from simplibs.file.logic._common.validations import raise_destination_is_dir_error


@pytest.mark.parametrize("operation", ["copy", "move", "write"])
@pytest.mark.parametrize("path", [Path("out/folder"), Path("some_dir")])
def test_raise_destination_is_dir_error_contract(subtests, path, operation) -> None:
    """Verify raise_destination_is_dir_error produces a well-formed StateError card."""

    def raising_wrapper(target_path):
        raise_destination_is_dir_error(target_path, operation)

    exc = assert_exception_function(
        subtests,
        raising_wrapper,
        invalid_params=(path,),
        exception_type=StateError,
        error_name=f"FILE_{operation.upper()}_DESTINATION_IS_DIRECTORY",
        label=f"destination '{path}'",
        value=str(path),
        problem=(
            f"Cannot {operation} onto '{path}'.",
            "A directory already occupies this path.",
        ),
        expected="A destination that is a file path — existing or not — never an existing directory.",
        how_to_fix=(
            "Give the full target path including the file name, e.g. 'folder/name.ext'.",
            "Choose a different name if a directory of that name must stay.",
        ),
        exception=IsADirectoryError,
        verbose=False,
    )

    # The card must be catchable as the stdlib type it wraps
    assert isinstance(exc, IsADirectoryError)
