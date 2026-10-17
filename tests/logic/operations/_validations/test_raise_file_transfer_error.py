from pathlib import Path
import pytest
from simplibs.exception.testing import assert_exception_function
from simplibs.exception import AccessError
from simplibs.file.logic.operations._validations import raise_file_transfer_error


@pytest.mark.parametrize("operation", ["copy", "move", "backup"])
@pytest.mark.parametrize(
    "source, destination",
    [
        (Path("in/a.txt"), Path("out/a.txt")),
        (Path("report.csv"), Path("archive/report.csv.bak")),
    ],
)
@pytest.mark.parametrize(
    "caught_exc",
    [PermissionError("denied"), OSError("disk full")],
    ids=["PermissionError", "OSError"],
)
def test_raise_file_transfer_error_contract(subtests, caught_exc, source, destination, operation) -> None:
    """Verify raise_file_transfer_error produces a well-formed AccessError card showing both paths."""

    def raising_wrapper(src):
        raise_file_transfer_error(src, destination, operation, caught_exc)

    exc = assert_exception_function(
        subtests,
        raising_wrapper,
        invalid_params=(source,),
        exception_type=AccessError,
        error_name=f"FILE_{operation.upper()}_FAILED",
        label=f"file '{source}' -> '{destination}'",
        value=str(destination),
        problem=(
            f"Failed to {operation} '{source}' to '{destination}'.",
            f"OS reported: {caught_exc}",
        ),
        expected=f"A readable source and a destination location where the process may {operation} to.",
        how_to_fix=(
            "Check read permission for the source and write permission for the destination folder.",
            "Make sure no other program is holding either file open.",
            "Verify that the destination storage has free space.",
        ),
        exception=type(caught_exc),
        verbose=False,
    )

    # The original OS exception type must survive
    assert isinstance(exc, type(caught_exc))
