from pathlib import Path
from simplibs.path import PathLike, ensure_parent_dir, normalize_path
# Outers
from ..._common.validations import (
    raise_destination_exists_error,
    raise_destination_is_dir_error,
    raise_file_access_error,
)


def prepare_write_target(
    path: PathLike,
    operation: str,
    *,
    overwrite: bool = True,
) -> Path:
    """Normalize a write target and make sure writing to it is allowed and possible.

    Args:
        path: The file about to be written or appended to.
        operation: `"write"` or `"append"` — used in the failure cards.
        overwrite: If False, an existing file at the target is refused.

    Returns:
        The normalized target `Path`, with its folder guaranteed to exist.

    Raises:
        StateError: If a directory occupies the target.
        AlreadyExistsError: If the target exists and `overwrite=False`.
        AccessError: If the OS refuses even the checks, or the folder cannot be created.
    """

    # 1. Normalize — a symlink is followed, the CONTENT behind it is written
    target = normalize_path(path)

    # 2. Ask the disk; a refusal is an access problem
    try:
        is_dir = target.is_dir()
        exists = target.exists()
    except OSError as caught_exc:
        raise_file_access_error(target, operation, caught_exc)

    # 3. A directory can never become a file
    if is_dir:
        raise_destination_is_dir_error(target, operation)

    # 4. An existing file is only replaced when the caller allows it
    if exists and not overwrite:
        raise_destination_exists_error(target, operation)

    # 5. Guarantee the folder the file will live in
    ensure_parent_dir(target)

    # 6. The prepared target
    return target


_DESIGN_NOTES = """
# prepare_write_target — the Shared Start of Every Byte Writer

## Purpose
`write_bytes` and `append_bytes` both begin with the same four things:
normalize, refuse a directory, honour `overwrite`, create the folder. Done
once here instead of twice (the old code repeated it in five writers).

## `exists` Is a Fail-Fast Message, Not a Lock
Between this check and the actual write another process may create the file.
Direct writes use exclusive mode (`"xb"`) to close that gap; the draft swap
cannot (`os.replace` overwrites), so with `use_draft=True` and
`overwrite=False` the check is best-effort. The docs say so.

## Overlap With `SafeFileWriter`
The writer repeats the folder and directory guard because it is also a public
class used on its own; both are idempotent and cost one `stat`.
"""
