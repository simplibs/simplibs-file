from pathlib import Path


def delete_draft(
    draft_path: Path | None,
) -> None:
    """Discard a draft file — quietly, whatever happens.

    Args:
        draft_path: The draft file to remove. `None` is accepted and ignored.
    """

    # 1. Nothing was ever created
    if draft_path is None:
        return

    # 2. Remove the draft; a failure here must never hide the error that led here
    try:
        draft_path.unlink(missing_ok=True)
    except OSError:
        pass


_DESIGN_NOTES = """
# delete_draft — Cleanup That Never Throws

## Purpose
Called on every failure path of `SafeFileWriter` and `create_draft`. If the
cleanup itself could raise, it would replace the ORIGINAL error (a full disk,
a permission problem) with a less useful one.

## What Is Accepted as the Price
In the rare case the draft cannot be removed (locked by an antivirus), an
orphan `.name.xxxxxxxx.draft` stays next to the target. `IGNORE_DRAFTS` keeps
scanners from collecting it.
"""
