from simplibs.actions import create_action
# Outers
from ...logic.operations import backup_file


BackupFile = create_action(
    backup_file,
    main_param="path",
    class_name="BackupFile",
)
"""Action wrapping `backup_file` — creates an atomic backup copy next to the file flowing in."""


_DESIGN_NOTES = """
# BackupFile — Action Over `backup_file`

## Purpose
`BackupFile() >> WriteText(path=...)` — back up, then overwrite safely.

## Shape
Main input: `path`. Path in, the BACKUP's `Path` out (not the original). Changes the disk.

## Changes the Disk
This action writes, copies, moves or deletes.
"""
