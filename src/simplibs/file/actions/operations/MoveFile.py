from simplibs.actions import create_action
# Outers
from ...logic.operations import move_file


MoveFile = create_action(
    move_file,
    main_param="source",
    class_name="MoveFile",
)
"""Action wrapping `move_file` — moves or renames the file flowing in to the configured `destination`."""


_DESIGN_NOTES = """
# MoveFile — Action Over `move_file`

## Purpose
Works across folders and across devices; a symlink is moved as a link.

## Shape
Main input: `source`. Source in, the destination `Path` out. `RenameFile` is the same operation under the old name.

## Changes the Disk
This action writes, copies, moves or deletes.
"""
