from simplibs.actions import create_action
# Outers
from ...logic.operations import copy_file


CopyFileFrom = create_action(
    copy_file,
    main_param="destination",
    class_name="CopyFileFrom",
)
"""Action wrapping `copy_file` — copies the configured `source` to the path flowing in."""


_DESIGN_NOTES = """
# CopyFileFrom — Action Over `copy_file`

## Purpose
One template copied to many destinations: `CollectDirs(...) >> ForEach(RebasePath(...) >> CopyFileFrom(source=template))`.

## Shape
Main input: `destination`. Destination in, the destination `Path` out. Sibling of `CopyFile` (there the source flows).

## Changes the Disk
This action writes, copies, moves or deletes.
"""
