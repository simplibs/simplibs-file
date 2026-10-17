import os
from pathlib import Path
from simplibs.path import PathLike, ensure_parent_dir, normalize_entry_path
from simplibs.validate import validate_call
# Outers
from .._common.validations import (
    raise_file_access_error,
    raise_file_not_found_error,
    raise_not_a_file_error,
)
from .._common.helpers import replace_with_retry
# Inners
from ._validations import raise_file_transfer_error
from ._helpers import (
    is_cross_device_error,
    move_across_devices,
    prepare_destination
)

@validate_call
def move_file(
    source: PathLike,
    destination: PathLike,
    *,
    overwrite: bool = False,
) -> Path:
    """Move or rename a file — across folders and across devices.

    Works on the directory ENTRY: a symlink is moved as a link, not as the file
    it points to.

    Args:
        source: The file (or symlink) to move.
        destination: The new FILE path. Its folder is created if missing.
        overwrite: If False (default), an existing destination raises.

    Returns:
        The normalized destination `Path`.

    Raises:
        NotFoundError: If the source does not exist.
        StateError: If the source is a directory, or a directory occupies the destination.
        ParamError: If source and destination are the same file.
        AlreadyExistsError: If the destination exists and `overwrite=False`.
        AccessError: If the OS refuses the move.
    """

    # 1. Entry semantics — a symlink in the final position stays a symlink
    source_path = normalize_entry_path(source)
    destination_path = normalize_entry_path(destination)

    # 2. The source must be an existing file entry
    try:
        exists = os.path.lexists(source_path)
        is_file_entry = exists and (source_path.is_symlink() or source_path.is_file())
    except OSError as caught_exc:
        raise_file_access_error(source_path, "move", caught_exc)
    if not exists:
        raise_file_not_found_error(source_path, "move")
    if not is_file_entry:
        raise_not_a_file_error(source_path, "move")

    # 3. Same file? a directory? already there?
    prepare_destination(source_path, destination_path, "move", overwrite=overwrite)

    # 4. Guarantee the destination's folder
    ensure_parent_dir(destination_path)

    # 5. One atomic rename
    try:
        replace_with_retry(source_path, destination_path)
    except OSError as caught_exc:

        # 5.1 Anything but "different device" is a real failure
        if not is_cross_device_error(caught_exc):
            raise_file_transfer_error(source_path, destination_path, "move", caught_exc)

        # 5.2 Different device — copy completely, then remove the source
        try:
            move_across_devices(source_path, destination_path)
        except OSError as fallback_exc:
            raise_file_transfer_error(source_path, destination_path, "move", fallback_exc)

    # 6. The new location
    return destination_path


_DESIGN_NOTES = """
# move_file — Rename and Move, Everywhere

## Renamed From `rename_file`
It always moved files, and the new name says so. `rename_file` stays as an alias.

## Fixed From the Old Version
* **Entry semantics.** `normalize_path` followed symlinks, so moving `link`
  moved the TARGET. `normalize_entry_path` keeps the link as the thing moved.
* **Across devices.** `os.replace` between `G:` and `C:` failed (`WinError 17`,
  `EXDEV`) although the docstring promised "or move". Now it falls back to an
  atomic copy followed by removing the source (`move_across_devices`).
* **Case-only rename on Windows** (`a.txt` -> `A.txt`) is allowed (see `prepare_destination`).
* **Windows locks** are retried like in `commit_draft` (`replace_with_retry`).
* A directory as the source is a clear card.

## No `sync`
A same-device rename has no data to flush; a power-loss guarantee for the
rename itself would need a folder `fsync` that Windows does not offer. The
parameter would promise more than it can keep.
"""
