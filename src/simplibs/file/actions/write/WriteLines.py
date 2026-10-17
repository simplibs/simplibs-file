from simplibs.actions import create_action
# Outers
from ...logic.write import write_lines


WriteLines = create_action(
    write_lines,
    main_param="lines",
    class_name="WriteLines",
)
"""Action wrapping `write_lines` — writes the lines flowing in to the configured `path`, one per line."""


_DESIGN_NOTES = """
# WriteLines — Action Over `write_lines`

## Purpose
`ReadLines() >> filter >> WriteLines(path=target)`.

## Shape
Main input: `lines`. A list of lines in, the written `Path` out. Sibling: `WriteLinesTo`.

## Changes the Disk
This action writes, copies, moves or deletes.
"""
