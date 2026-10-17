from .BackupFile import BackupFile
from .CopyFile import CopyFile
from .CopyFileFrom import CopyFileFrom
from .DeleteFile import DeleteFile
from .MoveFile import MoveFile
from .RenameFile import RenameFile


_DESIGN_NOTES = """
# File Actions Operations Sub-Package

## Purpose
Pipeline actions wrapping file manipulation functions (`copy_file`, `move_file`,
`delete_file`, and `backup_file`). These actions change the state of the disk.

## Internal Components Registry

| Component    | Type   | Description                                                 |
| :----------- | :----- | :---------------------------------------------------------- |
| `BackupFile` | Action | Creates an atomic backup copy next to the input file.       |
| `CopyFile`   | Action | Copies the input file to the configured destination.        |
| `CopyFileFrom`| Action| Copies the configured source file to the input destination. |
| `DeleteFile` | Action | Deletes the file or symlink entry flowing in.               |
| `MoveFile`   | Action | Moves or renames the input file to the destination.         |
| `RenameFile` | Action | Backward-compatible alias action wrapping `move_file`.      |
"""