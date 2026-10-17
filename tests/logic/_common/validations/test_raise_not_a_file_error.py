from pathlib import Path
import pytest
from simplibs.exception.testing import assert_exception_function
from simplibs.exception import StateError
from simplibs.file.logic._common.validations import raise_not_a_file_error


@pytest.mark.parametrize("operation", ["read", "hash", "inspect"])
@pytest.mark.parametrize("path", [Path("some_dir"), Path("sub/folder")])
def test_raise_not_a_file_error_contract(subtests, path, operation) -> None:
    """Verify raise_not_a_file_error produces a well-formed StateError card."""

    def raising_wrapper(target_path):
        raise_not_a_file_error(target_path, operation)

    exc = assert_exception_function(
        subtests,
        raising_wrapper,
        invalid_params=(path,),
        exception_type=StateError,
        error_name=f"FILE_{operation.upper()}_NOT_A_FILE",
        label=f"path '{path}'",
        value=str(path),
        problem=(
            f"Cannot {operation} '{path}'.",
            "Expected a regular file, but a directory or another kind of entry was found.",
        ),
        expected="A path pointing to a regular file.",
        how_to_fix=(
            "Provide the path of a file, not of a directory.",
            "To work with a directory, use the functions of simplibs-path.",
        ),
        exception=IsADirectoryError,
        verbose=False,
    )

    # The card must be catchable as the stdlib type it wraps
    assert isinstance(exc, IsADirectoryError)
