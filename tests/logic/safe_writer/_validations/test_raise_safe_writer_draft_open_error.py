from pathlib import Path
import pytest
from simplibs.exception.testing import assert_exception_function
from simplibs.exception import AccessError
from simplibs.file.logic.safe_writer._validations import raise_safe_writer_draft_open_error


@pytest.mark.parametrize("target_path", [Path("out/report.txt"), Path("data.json")])
@pytest.mark.parametrize(
    "caught_exc",
    [PermissionError("denied"), OSError("disk full")],
    ids=["PermissionError", "OSError"],
)
def test_raise_safe_writer_draft_open_error_contract(subtests, caught_exc, target_path) -> None:
    """Verify raise_safe_writer_draft_open_error produces a well-formed AccessError card."""

    def raising_wrapper(path):
        raise_safe_writer_draft_open_error(path, caught_exc)

    exc = assert_exception_function(
        subtests,
        raising_wrapper,
        invalid_params=(target_path,),
        exception_type=AccessError,
        error_name="SAFE_WRITER_DRAFT_OPEN_FAILED",
        label=f"draft for '{target_path}'",
        value=str(target_path),
        problem=(
            f"The draft file for '{target_path}' was created but could not be opened for writing.",
            f"OS reported: {caught_exc}",
        ),
        expected="A draft file the process may open for writing.",
        how_to_fix=(
            "Make sure no other program is holding the draft open (antivirus, indexer).",
            "Verify that the storage is healthy and has free space.",
        ),
        exception=type(caught_exc),
        verbose=False,
    )

    # The original OS exception type must survive
    assert isinstance(exc, type(caught_exc))
