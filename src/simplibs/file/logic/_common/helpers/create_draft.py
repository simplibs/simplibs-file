import os
import secrets
import shutil
from pathlib import Path
# Inners
from .delete_draft import delete_draft
from .shorten_draft_name import shorten_draft_name


# How many random names to try before giving up (a clash is astronomically rare)
_MAX_ATTEMPTS: int = 100


def create_draft(
    target_path: Path,
    *,
    append: bool,
) -> Path:
    """Create the unique, empty draft file a `SafeFileWriter` writes into.

    Args:
        target_path: The final file the draft will eventually replace.
        append: If True and `target_path` is an existing file, its current
            content is copied into the draft first, so later writes continue
            after it instead of starting from empty.

    Returns:
        The path of the new draft, in the same folder as `target_path`
        (required for an atomic swap), named `.<name>.<8 hex>.draft`.

    Raises:
        OSError: If no draft can be created or the existing content cannot be copied.
            Nothing is left behind in that case.
    """

    # 1. Reserve a unique name by creating the file exclusively — no race, no shared name
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0)
    base_name = shorten_draft_name(target_path.name)
    draft_path: Path | None = None
    for _ in range(_MAX_ATTEMPTS):
        candidate = target_path.with_name(f".{base_name}.{secrets.token_hex(4)}.draft")
        try:
            descriptor = os.open(candidate, flags, 0o666)
        except FileExistsError:
            continue
        os.close(descriptor)
        draft_path = candidate
        break

    # 2. Every candidate was taken
    if draft_path is None:
        raise FileExistsError(f"No free draft name found next to '{target_path}'.")

    # 3. Append mode — start from a copy of the existing content (data only, permissions are handled at commit)
    if append and target_path.is_file():
        try:
            shutil.copyfile(target_path, draft_path)
        except BaseException:
            delete_draft(draft_path)
            raise

    # 4. The ready draft
    return draft_path


_DESIGN_NOTES = """
# create_draft — a Unique Draft Next to the Target

## Purpose
The first step of every safe write: a private scratch file that later
replaces the target in one atomic step.

---

## 1. Unique Name Instead of `name.draft`
The old fixed name meant two writers of the same target shared (and
interleaved in) one draft, and a leftover from a crash was silently reused by
the next run. Now every draft has a random 8-hex part.

## 2. Own `O_CREAT | O_EXCL` Loop Instead of `tempfile.mkstemp`
`mkstemp` always creates the file with mode `0o600`. A NEW target written
through the writer would then be more private than a plain `open()` would make
it. Creating with `0o666` lets the umask decide, exactly like a normal write.
`O_EXCL` still guarantees nobody else owns that name. `O_BINARY` is added where
it exists (Windows) so no newline translation can happen at this level.

## 3. Same Folder as the Target
`os.replace` is only atomic within one filesystem. A draft next to the target
is always on the same one.

## 4. Name Length
`.<name>.<8hex>.draft` adds 16 characters; a long target name is cut by
`shorten_draft_name` (at most 100 characters AND few enough bytes) so that the
255 limit is never exceeded, also for multi-byte names on Linux and macOS.

## 5. Append Copies the Content
Appending to a file safely means: copy it, append to the copy, swap. The cost
grows with the file size — that is why `append_*` defaults to `use_draft=False`.

## Cleanup
A failure while copying removes the draft again; the caller never has to
clean up after a failed `create_draft`.
"""
