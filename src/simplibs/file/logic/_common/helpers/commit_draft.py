import os
import shutil
from pathlib import Path
# Outers
from ..._common.helpers import replace_with_retry


def commit_draft(
    draft_path: Path,
    target_path: Path,
    *,
    keep_mode: bool = True,
    sync: bool = False,
    attempts: int = 5,
    delay: float = 0.05,
) -> None:
    """Atomically replace `target_path` with the finished draft.

    Args:
        draft_path: The completed, closed draft file.
        target_path: The final destination the draft becomes.
        keep_mode: If True (default), the permissions of the file being replaced
            are copied onto the draft. A copy sets this to False, because it
            carries the permissions of its SOURCE.
        sync: If True, force the draft (and, where the OS allows, the folder)
            to stable storage — durable even across a power loss.
        attempts: How many times to try the swap on Windows when the target
            is momentarily locked (antivirus, indexer).
        delay: Base pause in seconds between attempts; grows with every attempt.

    Raises:
        OSError: If the swap fails (a permission problem, a locked file after
            every attempt, a directory at the target).
    """

    # 1. Keep the permissions of the file being replaced (a new inode would otherwise reset them)
    if keep_mode and target_path.is_file():
        try:
            shutil.copymode(target_path, draft_path)
        except OSError:
            pass

    # 2. Durability — make the draft's data reach the disk before it becomes the target
    if sync:
        with draft_path.open("r+b") as handle:
            os.fsync(handle.fileno())

    # 3. Swap; short Windows locks are retried inside
    replace_with_retry(draft_path, target_path, attempts=attempts, delay=delay)

    # 4. Durability — persist the rename itself (not possible on Windows; best effort elsewhere)
    if sync and os.name != "nt":
        try:
            descriptor = os.open(target_path.parent, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        except OSError:
            pass


_DESIGN_NOTES = """
# commit_draft — the Atomic Swap

## Purpose
Replaces `write_draft` (renamed: it does not "write" anything, it commits).
One `os.replace`: readers see either the complete old file or the complete
new one, never a mixture.

---

## 1. Permissions Survive
`os.replace` puts a NEW inode in place, so the target would get the mode of the
draft instead of its own. A `0o600` secrets file would silently become
`0o644` (or the other way round). `shutil.copymode` copies the mode of the old
file onto the draft first. On Windows `copymode` only carries the read-only flag.

## 2. Windows Lock Retry
Delegated to `replace_with_retry`, which `move_file` shares.

## 2b. `keep_mode=False`
A COPY must end up with the permissions of its source (`copy2` semantics),
not with those of the file it replaces; `copy_atomically` passes `False`.

## 3. `sync` — Honest Durability
Atomic means "safe against a crashing PROCESS". Against a power loss the data
must also be flushed: `fsync` the draft before the swap, and on POSIX the
folder after it. Windows cannot fsync a folder; there only the file is synced.

## Raises, Does Not Wrap
The caller (`SafeFileWriter`, `copy_atomically`) knows the context and builds
the failure card; this helper stays a thin OS step.
"""
