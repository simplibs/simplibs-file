from pathlib import Path
# Inners
from .copy_atomically import copy_atomically


def move_across_devices(
    source: Path,
    destination: Path,
    *,
    sync: bool = False,
) -> None:
    """Move a regular file to another device: atomic copy first, then remove the source.

    Args:
        source: The file to move.
        destination: The target path (on another device); its folder must exist.
        sync: If True, force the copy to stable storage before the source is removed.

    Raises:
        OSError: If the copy fails (nothing changed), the source is a symlink,
            or the source cannot be removed AFTER a successful copy (then both
            files exist — no data is ever lost).
    """

    # 1. A link is an entry pointing somewhere; copying its content would change what it is
    if source.is_symlink():
        raise OSError("A symbolic link cannot be moved to another device.")

    # 2. The copy is complete and in place first ...
    copy_atomically(source, destination, sync=sync)

    # 3. ... only then is the source removed
    source.unlink()


_DESIGN_NOTES = """
# move_across_devices — the Fallback of `move_file`

## Order Is the Safety
Copy fully, THEN delete. A failure at any point leaves at least one complete
file. The worst case (copy done, source locked) leaves two files, never none.

## Symlinks
Recreating a link elsewhere is a different operation (its target may be
relative); refused with a clear message instead of silently turning a link
into a file.

## TODO(test)
Simulated cross-device `os.replace` -> fallback runs; unlink failure after a successful copy.
"""
