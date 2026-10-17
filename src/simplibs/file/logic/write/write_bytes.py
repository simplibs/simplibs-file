import os
from pathlib import Path
from simplibs.exception import SimpleException
from simplibs.path import PathLike
from simplibs.validate import validate_call
# Outers
from .._common.validations import raise_destination_exists_error, raise_file_access_error
from ..safe_writer import SafeFileWriter
# Inners
from ._helpers import prepare_write_target


@validate_call
def write_bytes(
    path: PathLike,
    data: bytes,
    *,
    overwrite: bool = True,
    use_draft: bool = True,
    sync: bool = False,
) -> Path:
    """Write bytes to a file — the core every other writer is built on.

    Args:
        path: The target file. Its folder is created if missing.
        data: The bytes to write.
        overwrite: If False, an existing file raises instead of being replaced.
        use_draft: If True (default), the data goes into a draft that replaces
            the target atomically, so a failure never damages the old file.
            If False, the target is written in place (faster, but a failure
            can leave a partial file).
        sync: If True, force the data to stable storage (survives a power loss; slower).

    Returns:
        The normalized target `Path`.

    Raises:
        StateError: If a directory occupies the target.
        AlreadyExistsError: If the target exists and `overwrite=False`.
        AccessError: If the OS refuses the write.
    """

    # 1. Normalize, refuse a directory, honour overwrite, create the folder
    target = prepare_write_target(path, "write", overwrite=overwrite)

    # 2. Safe path — draft and swap
    if use_draft:
        try:
            with SafeFileWriter(target, mode="wb", sync=sync) as handle:
                handle.write(data)

        # 2.1 A card the writer already built passes through untouched
        except SimpleException:
            raise

        # 2.2 A raw OS failure while writing into the draft
        except OSError as caught_exc:
            raise_file_access_error(target, "write", caught_exc)
        return target

    # 3. Direct path — exclusive mode closes the check-then-write gap when overwriting is forbidden
    try:
        with target.open("wb" if overwrite else "xb") as handle:
            handle.write(data)
            if sync:
                handle.flush()
                os.fsync(handle.fileno())
    except FileExistsError:
        raise_destination_exists_error(target, "write")
    except OSError as caught_exc:
        raise_file_access_error(target, "write", caught_exc)

    # 4. Return the normalized path
    return target


_DESIGN_NOTES = """
# write_bytes — the First Core Writer

## Purpose
Every writer of the library ends here. Text, lines, aggregated text and JSON
are encoded to bytes IN MEMORY first, then handed to this function — so the
draft logic exists exactly once (it used to be copied into five functions) and
a conversion error can never leave a half-written file.

---

## 1. Parameters
* `overwrite=True` — now on every writer, not only on copy/move.
* `use_draft=True` — safe by default; `False` is the fast, in-place option.
* `sync=False` — durability against power loss on request.

## 2. Direct Write Is Honest About Its Risk
`use_draft=False` truncates the target first; a crash in the middle leaves a
partial file. That is the documented price of speed.

## 3. Card Pass-Through
`except SimpleException: raise` — cards raised by `SafeFileWriter` may
themselves be `OSError` subclasses (they keep the caught exception type); they
must not be caught by `except OSError` and wrapped a second time.

## 4. `overwrite=False` With a Draft
The existence check is a fail-fast message, not a guarantee: `os.replace`
overwrites silently if the file appears in the last millisecond. Direct mode
is exact (`"xb"`).

## TODO(test)
* Draft mode, `overwrite=False`, target appears in between (simulate) — documented behaviour.
* A card from `SafeFileWriter` is not double-wrapped.
* `sync=True` in both modes.
* `bytes`-only: `bytearray` is rejected by the annotation — keep or widen?
"""
