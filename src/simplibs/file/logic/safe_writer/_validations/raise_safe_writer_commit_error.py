from pathlib import Path
from typing import NoReturn
from simplibs.exception import AccessError


def raise_safe_writer_commit_error(
    target_path: Path,
    caught_exc: Exception,
) -> NoReturn:
    """Raise AccessError when a finished draft cannot replace the target file."""

    # 1. Raise structured AccessError wrapping the caught OS exception
    raise AccessError(
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
    )


_DESIGN_NOTES = """
# raise_safe_writer_commit_error — the Swap Failed

## Purpose
The last failure point of `SafeFileWriter`. Renamed from
`raise_safe_file_commit_error` to match the name the code actually called
(`raise_safe_writer_commit_error`).

## The Promise in the Text
"The original file is unchanged" is true: `os.replace` is atomic, so a
failed swap leaves the old content in place.
"""
