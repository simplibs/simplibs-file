from simplibs.actions import create_action
# Outers
from ...logic.write import write_bytes


WriteBytes = create_action(
    write_bytes,
    main_param="data",
    class_name="WriteBytes",
)
"""Action wrapping `write_bytes` — writes the bytes flowing in to the configured `path`."""


_DESIGN_NOTES = """
# WriteBytes — Action Over `write_bytes`

## Purpose
The last step of a pipeline that produces binary output: `... >> WriteBytes(path=target)`.

## Shape
Main input: `data`. Content in, the written `Path` out. Sibling: `WriteBytesTo` (the path flows, the data is configuration).

## Changes the Disk
This action writes, copies, moves or deletes.
"""
