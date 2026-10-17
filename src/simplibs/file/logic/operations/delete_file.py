import os
import stat
from pathlib import Path
from simplibs.path import PathLike, normalize_entry_path
from simplibs.validate import validate_call
# Outers
from .._common.validations import (
    raise_file_access_error,
    raise_file_not_found_error,
    raise_not_a_file_error,
)


@validate_call
def delete_file(
    path: PathLike,
    *,
    missing_ok: bool = False,
    force: bool = False,
) -> Path:
    """Delete a file — or a symlink, without touching what it points to.

    Args:
        path: The file or symlink to delete.
        missing_ok: If True, a missing path is accepted silently.
        force: If True, a read-only file is made writable first (a problem
            on Windows, where read-only files cannot be deleted).

    Returns:
        The normalized path of the (now deleted) entry.

    Raises:
        NotFoundError: If nothing exists there and `missing_ok=False`.
        StateError: If the path is a directory.
        AccessError: If the OS refuses the deletion.
    """

    # 1. Entry semantics — "link" means the link itself
    entry = normalize_entry_path(path)

    # 2. Ask the disk about the ENTRY (a dangling symlink exists as an entry)
    try:
        exists = os.path.lexists(entry)
        is_file_entry = exists and (entry.is_symlink() or entry.is_file())
    except OSError as caught_exc:
        raise_file_access_error(entry, "delete", caught_exc)

    # 3. Missing
    if not exists:
        if missing_ok:
            return entry
        raise_file_not_found_error(entry, "delete")

    # 4. A directory (or a special entry) is not something this function deletes
    if not is_file_entry:
        raise_not_a_file_error(entry, "delete")

    # 5. Delete
    try:
        entry.unlink()

    # 5.1 It vanished since the check
    except FileNotFoundError as caught_exc:
        if not missing_ok:
            raise_file_not_found_error(entry, "delete")

    # 5.2 Read-only (Windows) — with `force` clear the flag and try once more
    except PermissionError as caught_exc:
        if not force:
            raise_file_access_error(entry, "delete", caught_exc)
        try:
            if not entry.is_symlink():
                os.chmod(entry, stat.S_IWRITE)
            entry.unlink()
        except OSError as retry_exc:
            raise_file_access_error(entry, "delete", retry_exc)

    # 5.3 Any other OS refusal
    except OSError as caught_exc:
        raise_file_access_error(entry, "delete", caught_exc)

    # 6. The deleted entry's path
    return entry


_DESIGN_NOTES = """
# delete_file — Delete the Entry, Not Its Target

## Fixed From the Old Version
`normalize_path` followed symlinks, so `delete_file("link")` deleted the FILE
the link pointed to and left the dangling link behind. `normalize_entry_path`
resolves only the folder; the link itself is what `unlink` removes. A dangling
link can be deleted too.

## New: Type Check and `force`
* A directory raises a clear `StateError` (the old code reached `unlink` and got
  a raw `PermissionError` or `IsADirectoryError`).
* `force=True` clears the read-only flag, because on Windows a read-only file
  cannot be deleted. Off by default: removing a protection is an explicit choice.
  The flag of a symlink's TARGET is never touched.

## Race
A file removed by someone else between the check and `unlink` is the same
outcome the caller wanted with `missing_ok=True`, and an honest "not found"
otherwise.

## TODO(test)
Symlink -> target survives; dangling symlink; directory; read-only file with and
without `force` (Windows); `missing_ok`.
"""
