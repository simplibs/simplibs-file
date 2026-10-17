import os
from pathlib import Path
from simplibs.exception import SimpleException
from simplibs.path import PathLike
from simplibs.validate import validate_call
# Outers
from .._common.validations import raise_file_access_error
from ..safe_writer import SafeFileWriter
# Inners
from ._helpers import prepare_write_target


@validate_call
def append_bytes(
    path: PathLike,
    data: bytes,
    *,
    use_draft: bool = False,
    sync: bool = False,
) -> Path:
    """Append bytes to a file, creating it if it does not exist — the second core writer.

    Args:
        path: The target file. Its folder is created if missing.
        data: The bytes to add after the existing content.
        use_draft: If True, the existing content is copied into a draft, the
            data appended there, and the draft swapped in — an interrupted
            append can never damage the old content, but the cost grows with
            the file size. If False (default), the data is appended in place.
        sync: If True, force the data to stable storage (survives a power loss; slower).

    Returns:
        The normalized target `Path`.

    Raises:
        StateError: If a directory occupies the target.
        AccessError: If the OS refuses the write.
    """

    # 1. Normalize, refuse a directory, create the folder (appending never conflicts with an existing file)
    target = prepare_write_target(path, "append")

    # 2. Safe path — the draft starts as a copy of the existing content
    if use_draft:
        try:
            with SafeFileWriter(target, mode="ab", sync=sync) as handle:
                handle.write(data)

        # 2.1 A card the writer already built passes through untouched
        except SimpleException:
            raise

        # 2.2 A raw OS failure while writing into the draft
        except OSError as caught_exc:
            raise_file_access_error(target, "append", caught_exc)
        return target

    # 3. Direct path — a plain append
    try:
        with target.open("ab") as handle:
            handle.write(data)
            if sync:
                handle.flush()
                os.fsync(handle.fileno())
    except OSError as caught_exc:
        raise_file_access_error(target, "append", caught_exc)

    # 4. Return the normalized path
    return target


_DESIGN_NOTES = """
# append_bytes — the Second Core Writer

## Purpose
The twin of `write_bytes` for adding to a file. `append_text` encodes and
calls this.

## `use_draft=False` by Default
A safe append has to copy the whole existing file into a draft first, so the
cost grows with every append (appending a log line to a 1 GB file would copy
1 GB). The in-place append is fast, and an interrupted one can at worst leave
a partial LAST chunk — the older content is never touched. Whoever needs the
all-or-nothing guarantee asks for it with `use_draft=True`.

## No `overwrite`
Appending to an existing file is the whole point.

## TODO(test)
* Appending to a missing file creates it.
* `use_draft=True` on a file that changes during the append — last writer wins (documented).
* Direct append of an empty `bytes` creates an empty file.
"""
