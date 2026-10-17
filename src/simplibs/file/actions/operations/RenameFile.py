from simplibs.actions import create_action
# Outers
from ...logic.operations import move_file


RenameFile = create_action(
    move_file,
    main_param="source",
    class_name="RenameFile",
)
"""Action wrapping `move_file` — renames or moves the file flowing in to the configured `destination` — the old name of `MoveFile`."""


_DESIGN_NOTES = """
# RenameFile — Action Over `move_file`

## Purpose
Pipelines written against `rename_file` keep reading naturally.

## Shape
Main input: `source`. A separate class over the same function (instead of an alias of `MoveFile`) so that logs and tracebacks say `RenameFile`.

## Changes the Disk
This action writes, copies, moves or deletes.
"""
