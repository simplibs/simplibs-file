import os
import stat
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

    # 3. Windows cannot delete a read-only file — and a draft inherits that flag from a read-only target
    #    before the swap fails. The draft is our own private file, so the flag is cleared and the removal retried.
    except PermissionError:
        if os.name != "nt" or not draft_path.is_file():
            return
        try:
            os.chmod(draft_path, stat.S_IWRITE)
            draft_path.unlink(missing_ok=True)
        except OSError:
            pass
    except OSError:
        pass


_DESIGN_NOTES = """
# delete_draft — Cleanup That Never Throws

## Purpose
Called on every failure path of `SafeFileWriter` and `create_draft`. If the
cleanup itself could raise, it would replace the ORIGINAL error (a full disk,
a permission problem) with a less useful one.

## A Read-Only Draft (Windows)
`commit_draft` copies the permissions of the file being replaced onto the draft
before the swap. When that file is read-only, the draft becomes read-only too,
the swap fails — and a read-only file cannot be deleted on Windows. Without the
retry the cleanup would silently leave an orphan draft behind. The flag is
cleared only on Windows, only for a regular file, and only for this private draft.

## What Is Accepted as the Price
In the rare case the draft cannot be removed (locked by an antivirus), an
orphan `.name.xxxxxxxx.draft` stays next to the target. `IGNORE_DRAFTS` keeps
scanners from collecting it.
"""
