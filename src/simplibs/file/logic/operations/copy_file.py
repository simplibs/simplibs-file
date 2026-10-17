from pathlib import Path
from simplibs.path import PathLike, ensure_parent_dir, normalize_path
from simplibs.validate import validate_call
# Outers
from .._common.helpers import resolve_source_file
# Inners
from ._helpers import copy_atomically, prepare_destination
from ._validations import raise_file_transfer_error


@validate_call
def copy_file(
    source: PathLike,
    destination: PathLike,
    *,
    overwrite: bool = False,
    sync: bool = False,
) -> Path:
    """Copy a file to a new path, keeping its permissions and times.

    The copy is atomic: the destination is either the complete copy or
    untouched, never a truncated file.

    Args:
        source: The file to copy (a symlink is followed).
        destination: The target FILE path — never a folder to copy into.
            Its folder is created if missing.
        overwrite: If False (default), an existing destination raises.
        sync: Force the copy to stable storage.

    Returns:
        The normalized destination `Path`.

    Raises:
        NotFoundError, StateError: If the source is missing or not a file.
        ParamError: If source and destination are the same file.
        StateError: If a directory occupies the destination.
        AlreadyExistsError: If the destination exists and `overwrite=False`.
        AccessError: If the OS refuses the copy.
    """

    # 1. A verified source and a normalized destination
    source_path = resolve_source_file(source, "copy")
    destination_path = normalize_path(destination)

    # 2. Same file? a directory? already there?
    prepare_destination(source_path, destination_path, "copy", overwrite=overwrite)

    # 3. Guarantee the destination's folder
    ensure_parent_dir(destination_path)

    # 4. Copy through a draft; an OS failure becomes a card showing both paths
    try:
        copy_atomically(source_path, destination_path, sync=sync)
    except OSError as caught_exc:
        raise_file_transfer_error(source_path, destination_path, "copy", caught_exc)

    # 5. The guaranteed copy
    return destination_path


_DESIGN_NOTES = """
# copy_file — an Atomic, Honest Copy

## Fixed From the Old Version
* **Destination is a file path.** `shutil.copy2(src, folder)` copies INTO the
  folder, while the old function returned the folder's path — with
  `overwrite=True` a silent mismatch. An existing directory is now a `StateError`.
* **Atomic** (`copy_atomically`): no truncated copy after an interruption.
* **Same file refused** instead of truncating it.
* **Type checked**: a directory as the source is a card, not a raw OSError.

## Content Semantics
Source and destination are normalized with `normalize_path` (symlinks
resolved): the CONTENT is copied to where the destination path leads.
"""
