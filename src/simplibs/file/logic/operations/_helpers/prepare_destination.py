import os
from pathlib import Path
# Outers
from ..._common.validations import (
    raise_destination_exists_error,
    raise_destination_is_dir_error,
    raise_file_access_error,
)
from .._validations import (
    raise_same_file_error,
)


def prepare_destination(
    source: Path,
    destination: Path,
    operation: str,
    *,
    overwrite: bool,
) -> None:
    """Check that a source may be copied or moved onto a destination.

    Args:
        source: The normalized source path.
        destination: The normalized destination path.
        operation: `"copy"` or `"move"` — used in the failure cards.
        overwrite: If False, an existing destination is refused.

    Raises:
        ParamError: If source and destination are the same file.
        StateError: If a directory occupies the destination.
        AlreadyExistsError: If the destination exists and `overwrite=False`.
        AccessError: If the OS refuses even the checks.
    """

    # 1. The very same path (compared as TEXT: on Windows `Path('a.txt') == Path('A.txt')`,
    #    which would hide a legitimate case-only rename from step 4.1)
    if str(destination) == str(source):
        raise_same_file_error(destination, operation)

    # 2. Ask the disk about the destination ENTRY (a dangling link counts as existing)
    try:
        exists = os.path.lexists(destination)
        is_dir = exists and destination.is_dir() and not destination.is_symlink()
    except OSError as caught_exc:
        raise_file_access_error(destination, operation, caught_exc)

    # 3. A directory can never be replaced by a file
    if is_dir:
        raise_destination_is_dir_error(destination, operation)

    # 4. Another spelling of the same file (a hard link, a differently-cased name on Windows)
    if exists:
        try:
            same_file = os.path.samefile(source, destination)
        except OSError:
            same_file = False

        if same_file:

            # 4.1 Changing only the letter case of a name is a legitimate rename
            case_change = operation == "move" and str(destination).casefold() == str(source).casefold()
            if not case_change:
                raise_same_file_error(destination, operation)
            return

    # 5. An existing destination is only replaced when the caller allows it
    if exists and not overwrite:
        raise_destination_exists_error(destination, operation)


_DESIGN_NOTES = """
# prepare_destination — Is This Destination Acceptable?

## Purpose
The same four questions for `copy_file` and `move_file`: same file? a
directory? something already there? Answered once. The caller decides HOW the
paths were normalized (content semantics for a copy, entry semantics for a
move).

## Case-Only Rename
On Windows `a.txt` -> `A.txt` is the same file, yet a valid rename. For a
`"move"` with names that differ only in case, the same-file refusal is skipped.
Step 1 therefore compares the paths as TEXT: `Path` equality is case-insensitive
on Windows and would refuse the rename before step 4.1 could allow it.

## `lexists`
A dangling symlink at the destination is an existing ENTRY; a plain `exists()`
would call it free and the later replace would silently remove the link.
This applies to `move_file` (entry semantics). `copy_file` normalizes its
destination with `normalize_path`, so a dangling link has already been resolved
to the free path it points at and never reaches this check as a link.


"""
