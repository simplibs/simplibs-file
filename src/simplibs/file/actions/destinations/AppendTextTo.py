from simplibs.actions import create_action
# Outers
from ...logic.write import append_text


AppendTextTo = create_action(
    append_text,
    main_param="path",
    class_name="AppendTextTo",
)
"""Action wrapping `append_text` — appends the configured `text` to the path flowing in."""


_DESIGN_NOTES = """
# AppendTextTo — Action Over `append_text`

## Purpose
The same line added to several files.

## Shape
Main input: `path`. Path in, the target `Path` out. Sibling of `AppendText`.

## Changes the Disk
This action writes, copies, moves or deletes.
"""
