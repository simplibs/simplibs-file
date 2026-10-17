from simplibs.actions import create_action
# Outers
from ...logic.write import write_lines


WriteLinesTo = create_action(
    write_lines,
    main_param="path",
    class_name="WriteLinesTo",
)
"""Action wrapping `write_lines` — writes the configured `lines` to the path flowing in."""


_DESIGN_NOTES = """
# WriteLinesTo — Action Over `write_lines`

## Purpose
The same list of lines (a header, an ignore list) written to every path.

## Shape
Main input: `path`. Path in, the written `Path` out. Sibling of `WriteLines`.

## Changes the Disk
This action writes, copies, moves or deletes.
"""
