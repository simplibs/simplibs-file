from simplibs.actions import create_action
# Outers
from ...logic.write import write_text


WriteTextTo = create_action(
    write_text,
    main_param="path",
    class_name="WriteTextTo",
)
"""Action wrapping `write_text` — writes the configured `text` to the path flowing in."""


_DESIGN_NOTES = """
# WriteTextTo — Action Over `write_text`

## Purpose
A template or placeholder written to every path of a list: `ForEach(WriteTextTo(text="# TODO\n"))`.

## Shape
Main input: `path`. Path in, the written `Path` out. Sibling of `WriteText` (there the text flows).

## Changes the Disk
This action writes, copies, moves or deletes.
"""
