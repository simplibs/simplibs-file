from pathlib import Path
from typing import NoReturn
from simplibs.exception import AccessError


def raise_safe_writer_draft_open_error(
    target_path: Path,
    caught_exc: Exception,
) -> NoReturn:
    """Raise AccessError when a SafeFileWriter created its draft but cannot open it."""

    # 1. Raise structured AccessError wrapping the caught OS exception
    raise AccessError(
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
    )


_DESIGN_NOTES = """
# raise_safe_writer_draft_open_error — the Draft Exists, but Will Not Open

## Purpose
The old `SafeFileWriter.__enter__` let this failure escape raw AND left the
just-created draft behind. The writer now deletes the draft before raising
this card. The target file is untouched.
"""
