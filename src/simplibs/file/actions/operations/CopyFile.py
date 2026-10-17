from simplibs.actions import create_action
# Outers
from ...logic.operations import copy_file


CopyFile = create_action(
    copy_file,
    main_param="source",
    class_name="CopyFile",
)
"""Action wrapping `copy_file` — copies the file flowing in to the configured `destination`."""


_DESIGN_NOTES = """
# CopyFile — Action Over `copy_file`

## Purpose
`CopyFile(destination="backup/a.txt")("a.txt")`; atomic, keeps permissions and times.

## Shape
Main input: `source`. Source in, the destination `Path` out. Sibling: `CopyFileFrom`.

## Changes the Disk
This action writes, copies, moves or deletes.
"""
