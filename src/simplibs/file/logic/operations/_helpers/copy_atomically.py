import shutil
from pathlib import Path
# Outers
from ..._common.helpers import commit_draft, create_draft, delete_draft


def copy_atomically(
    source: Path,
    destination: Path,
    *,
    sync: bool = False,
) -> None:
    """Copy a file so that `destination` is either the complete copy or untouched.

    Args:
        source: An existing regular file.
        destination: The target path; its folder must already exist.
        sync: If True, force the copy to stable storage before it becomes visible.

    Raises:
        OSError: If the copy fails. Nothing is left behind and an existing
            destination is unchanged.
    """

    # 1. A private draft next to the destination — the same place a SafeFileWriter would use
    draft_path = create_draft(destination, append=False)

    # 2. Copy the data and the metadata (permissions, times) into it, then swap it in
    try:
        shutil.copyfile(source, draft_path)
        shutil.copystat(source, draft_path)
        commit_draft(draft_path, destination, keep_mode=False, sync=sync)

    # 3. Whatever went wrong, the draft goes away and the error continues
    except BaseException:
        delete_draft(draft_path)
        raise


_DESIGN_NOTES = """
# copy_atomically — a Copy That Cannot Be Half-Done

## Purpose
`shutil.copy2` writes straight into the destination: an interruption leaves a
truncated file that looks complete. For a BACKUP that is the worst possible
failure. Here the copy goes into a draft and is swapped in at the end — the
same mechanism as `SafeFileWriter`, reusing its three draft helpers.

## Metadata
`copyfile` + `copystat` is what `copy2` does: permissions and times of the
source. `keep_mode=False` stops `commit_draft` from overwriting those with the
mode of a destination being replaced.

## Used By
`copy_file`, `backup_file`, and the cross-device fallback of `move_file`.


"""
