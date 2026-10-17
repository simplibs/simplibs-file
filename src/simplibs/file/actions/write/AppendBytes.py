from simplibs.actions import create_action
# Outers
from ...logic.write import append_bytes


AppendBytes = create_action(
    append_bytes,
    main_param="data",
    class_name="AppendBytes",
)
"""Action wrapping `append_bytes` — appends the bytes flowing in to the configured `path`."""


_DESIGN_NOTES = """
# AppendBytes — Action Over `append_bytes`

## Purpose
Collecting binary chunks into one file as they are produced.

## Shape
Main input: `data`. Content in, the target `Path` out. Sibling: `AppendBytesTo`.

## Changes the Disk
This action writes, copies, moves or deletes.
"""
