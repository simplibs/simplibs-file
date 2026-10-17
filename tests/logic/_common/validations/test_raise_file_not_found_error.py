from pathlib import Path
import pytest
from simplibs.exception.testing import assert_exception_function
from simplibs.exception import NotFoundError
from simplibs.file.logic._common.validations import raise_file_not_found_error


@pytest.mark.parametrize("operation", ["read", "copy", "delete", "hash"])
@pytest.mark.parametrize("path", [Path("missing.txt"), Path("config/settings.json")])
def test_raise_file_not_found_error_contract(subtests, path, operation) -> None:
    """Verify raise_file_not_found_error produces a well-formed NotFoundError card."""

    def raising_wrapper(target_path):
        raise_file_not_found_error(target_path, operation)

    exc = assert_exception_function(
        subtests,
        raising_wrapper,
        invalid_params=(path,),
        exception_type=NotFoundError,
        error_name=f"FILE_{operation.upper()}_NOT_FOUND",
        label=f"file '{path}'",
        value=str(path),
        problem=f"Cannot {operation} '{path}': no such file exists.",
        expected="A path to an existing file.",
        how_to_fix=(
            "Check the spelling of the path and the current working directory.",
            "Make sure the file was created before this step runs.",
        ),
        exception=FileNotFoundError,
        verbose=False,
    )

    # The card must be catchable as the stdlib type it wraps
    assert isinstance(exc, FileNotFoundError)
