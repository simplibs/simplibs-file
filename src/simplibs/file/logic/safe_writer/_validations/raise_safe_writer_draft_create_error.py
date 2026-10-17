from pathlib import Path
from typing import NoReturn
from simplibs.exception import AccessError


def raise_safe_writer_draft_create_error(
    target_path: Path,
    caught_exc: Exception,
) -> NoReturn:
    """Raise AccessError when a SafeFileWriter cannot create its draft file."""

    # 1. Raise structured AccessError wrapping the caught OS exception
    raise AccessError(
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
    )


_DESIGN_NOTES = """
# raise_safe_writer_draft_create_error — No Room for a Draft

## Purpose
The first of three `SafeFileWriter` failure points. The target file has not
been touched when this is raised.
"""
