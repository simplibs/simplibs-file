from pathlib import Path
import pytest
from simplibs.exception.testing import assert_exception_function
from simplibs.exception import AccessError
from simplibs.file.logic.safe_writer._validations import raise_safe_writer_commit_error


@pytest.mark.parametrize("target_path", [Path("out/report.txt"), Path("data.json")])
@pytest.mark.parametrize(
    "caught_exc",
    [PermissionError("denied"), OSError("disk full")],
    ids=["PermissionError", "OSError"],
)
def test_raise_safe_writer_commit_error_contract(subtests, caught_exc, target_path) -> None:
    """Verify raise_safe_writer_commit_error produces a well-formed AccessError card."""

    def raising_wrapper(path):
        raise_safe_writer_commit_error(path, caught_exc)

    exc = assert_exception_function(
        subtests,
        raising_wrapper,
        invalid_params=(target_path,),
        exception_type=AccessError,
        error_name="SAFE_WRITER_COMMIT_FAILED",
        label=f"file '{target_path}'",
        value=str(target_path),
        problem=(
            f"The finished draft could not replace '{target_path}'.",
            f"OS reported: {caught_exc}",
            "The original file is unchanged and the draft was discarded.",
        ),
        expected="A target file that may be replaced.",
        how_to_fix=(
            "Close any program that has the target open (an editor, a viewer).",
            "On Windows, antivirus and indexers can lock a file for a moment — try again.",
            f"Check write permission for '{target_path.parent}'.",
        ),
        exception=type(caught_exc),
        verbose=False,
    )

    # The original OS exception type must survive
    assert isinstance(exc, type(caught_exc))
