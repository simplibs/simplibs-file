from pathlib import Path
import pytest
from simplibs.exception.testing import assert_exception_function
from simplibs.exception import AccessError
from simplibs.file.logic.safe_writer._validations import raise_safe_writer_draft_create_error


@pytest.mark.parametrize("target_path", [Path("out/report.txt"), Path("data.json")])
@pytest.mark.parametrize(
    "caught_exc",
    [PermissionError("denied"), OSError("disk full")],
    ids=["PermissionError", "OSError"],
)
def test_raise_safe_writer_draft_create_error_contract(subtests, caught_exc, target_path) -> None:
    """Verify raise_safe_writer_draft_create_error produces a well-formed AccessError card."""

    def raising_wrapper(path):
        raise_safe_writer_draft_create_error(path, caught_exc)

    exc = assert_exception_function(
        subtests,
        raising_wrapper,
        invalid_params=(target_path,),
        exception_type=AccessError,
        error_name="SAFE_WRITER_DRAFT_CREATE_FAILED",
        label=f"draft for '{target_path}'",
        value=str(target_path),
        problem=(
            f"Could not create a draft file next to '{target_path}'.",
            f"OS reported: {caught_exc}",
        ),
        expected="A writable folder with free space where a temporary draft can be created.",
        how_to_fix=(
            f"Check write permission for the folder '{target_path.parent}'.",
            "Verify that the storage has free space.",
            "Write directly with use_draft=False if drafts are not wanted here.",
        ),
        exception=type(caught_exc),
        verbose=False,
    )

    # The original OS exception type must survive
    assert isinstance(exc, type(caught_exc))
