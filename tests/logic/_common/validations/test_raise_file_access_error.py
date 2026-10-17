from pathlib import Path
import pytest
from simplibs.exception.testing import assert_exception_function
from simplibs.exception import AccessError
from simplibs.file.logic._common.validations import raise_file_access_error


@pytest.mark.parametrize("operation", ["read", "write", "append", "delete"])
@pytest.mark.parametrize("path", [Path("locked/file.txt"), Path("data.bin")])
@pytest.mark.parametrize(
    "caught_exc",
    [PermissionError("denied"), OSError("disk full"), FileNotFoundError("gone")],
    ids=["PermissionError", "OSError", "FileNotFoundError"],
)
def test_raise_file_access_error_contract(subtests, caught_exc, path, operation) -> None:
    """Verify raise_file_access_error produces a well-formed AccessError card."""

    def raising_wrapper(target_path):
        raise_file_access_error(target_path, operation, caught_exc)

    exc = assert_exception_function(
        subtests,
        raising_wrapper,
        invalid_params=(path,),
        exception_type=AccessError,
        error_name=f"FILE_{operation.upper()}_FAILED",
        label=f"file '{path}'",
        value=str(path),
        problem=(
            f"Failed to {operation} file '{path}'.",
            f"OS reported: {caught_exc}",
        ),
        expected=f"A file the process is allowed to {operation}, on a healthy filesystem.",
        how_to_fix=(
            f"Check that you have permission to {operation} '{path}'.",
            "Make sure no other program (editor, antivirus, indexer) is holding the file open.",
            "Verify that the storage is mounted and has free space.",
        ),
        exception=type(caught_exc),
        verbose=False,
    )

    # The original OS exception type must survive, so `except PermissionError` etc. keeps working
    assert isinstance(exc, type(caught_exc))
