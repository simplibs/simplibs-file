from pathlib import Path
from simplibs.path import PathLike, make_unique_path
from simplibs.path.tools import is_valid_suffix
from simplibs.validate import validate_call
# Outers
from .._common.helpers import resolve_source_file
# Inners
from ._helpers import build_timestamp, copy_atomically
from ._validations import (
    raise_file_transfer_error,
    raise_invalid_suffix_error,
    raise_same_file_error,
)


@validate_call
def backup_file(
    path: PathLike,
    *,
    suffix: str = ".bak",
    timestamp: bool = True,
    sync: bool = False,
) -> Path:
    """Create a backup copy of a file next to it, never overwriting an older backup.

    The copy is atomic: a backup is either complete or does not exist.

    Args:
        path: The file to back up.
        suffix: Appended to the backup's name. Defaults to `".bak"`; `""` is allowed.
        timestamp: If True (default), a `YYYYMMDD_HHMMSS` stamp is inserted
            before the extension.
        sync: Force the backup to stable storage.

    Returns:
        The normalized path of the new backup, e.g. `report_20261013_142530.txt.bak`.

    Raises:
        ParamError: If `suffix` is malformed, or the backup name would equal the source.
        NotFoundError, StateError: If the source is missing or not a file.
        OperationError: If no free numbered name can be found.
        AccessError: If the OS refuses the copy.
    """

    # 1. A malformed suffix would produce names like "report.txtbak"
    if not is_valid_suffix(suffix):
        raise_invalid_suffix_error(suffix, "backup")

    # 2. A verified source
    source = resolve_source_file(path, "backup")

    # 3. Build the backup's name: <stem>[_<timestamp>]<extension><suffix>
    name_parts = [source.stem]
    if timestamp:
        name_parts.append(build_timestamp())
    candidate = source.with_name("_".join(name_parts) + source.suffix + suffix)

    # 4. Without a stamp and a suffix the "backup" would be the source itself
    if candidate == source:
        raise_same_file_error(source, "backup")

    # 5. Two backups within one second must not overwrite each other
    backup_path = make_unique_path(candidate)

    # 6. Copy through a draft
    try:
        copy_atomically(source, backup_path, sync=sync)
    except OSError as caught_exc:
        raise_file_transfer_error(source, backup_path, "backup", caught_exc)

    # 7. The finished backup
    return backup_path


_DESIGN_NOTES = """
# backup_file — a Backup That Cannot Be Half-Made or Overwritten

## Fixed From the Old Version
* **No silent overwrite.** The stamp has a one-second resolution; two backups in
  the same second got the same name and `copy2` replaced the first.
  `make_unique_path` turns the second into `... (1)`.
* **Atomic.** An interrupted `shutil.copy2` left a truncated `.bak` that looked
  like a real backup — the worst failure a backup can have.
* **Suffix validated** (`is_valid_suffix`), and `timestamp=False` with
  `suffix=""` (a "backup" equal to the source) is a `ParamError`.
* **Testable clock** via `build_timestamp`.
* Type checked: a directory is a card, not a raw OSError.

## Name Shape
`<stem>[_<timestamp>]<extension><suffix>` — unchanged from the old version, so
existing backups keep the same look.

## Where the Backup Lives
Next to the REAL file: the source is normalized with symlinks resolved.

## Race
`make_unique_path` only looks; between its answer and the swap another process
could create that name. Accepted (documented), as for `overwrite=False` elsewhere.
"""
