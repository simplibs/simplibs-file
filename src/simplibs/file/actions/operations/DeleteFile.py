from simplibs.actions import create_action
# Outers
from ...logic.operations import delete_file


DeleteFile = create_action(
    delete_file,
    main_param="path",
    class_name="DeleteFile",
)
"""Action wrapping `delete_file` — deletes the file or symlink flowing in (the link itself, never its target)."""


_DESIGN_NOTES = """
# DeleteFile — Action Over `delete_file`

## Purpose
A cleanup step: `... >> DeleteFile(missing_ok=True)`.

## Shape
Main input: `path`. Path in, the deleted entry's `Path` out. Changes the disk.

## Changes the Disk
This action writes, copies, moves or deletes.
"""
