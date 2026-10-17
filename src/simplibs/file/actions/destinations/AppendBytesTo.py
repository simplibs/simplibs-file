from simplibs.actions import create_action
# Outers
from ...logic.write import append_bytes


AppendBytesTo = create_action(
    append_bytes,
    main_param="path",
    class_name="AppendBytesTo",
)
"""Action wrapping `append_bytes` — appends the configured `data` to the path flowing in."""


_DESIGN_NOTES = """
# AppendBytesTo — Action Over `append_bytes`

## Purpose
A fixed marker appended to each of several files.

## Shape
Main input: `path`. Path in, the target `Path` out. Sibling of `AppendBytes`.

## Changes the Disk
This action writes, copies, moves or deletes.
"""
