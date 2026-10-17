from simplibs.actions import create_action
# Outers
from ...logic.write import write_bytes


WriteBytesTo = create_action(
    write_bytes,
    main_param="path",
    class_name="WriteBytesTo",
)
"""Action wrapping `write_bytes` — writes the configured `data` to the path flowing in."""


_DESIGN_NOTES = """
# WriteBytesTo — Action Over `write_bytes`

## Purpose
The same bytes to many files: `CollectPaths(...) >> ForEach(WriteBytesTo(data=b""))`.

## Shape
Main input: `path`. Path in, the written `Path` out. Sibling of `WriteBytes` (there the content flows).

## Changes the Disk
This action writes, copies, moves or deletes.
"""
