from simplibs.actions import create_action
# Outers
from ...logic.write import write_text


WriteText = create_action(
    write_text,
    main_param="text",
    class_name="WriteText",
)
"""Action wrapping `write_text` — writes the text flowing in to the configured `path`."""


_DESIGN_NOTES = """
# WriteText — Action Over `write_text`

## Purpose
`ReadText() >> transform >> WriteText(path=target)` — the text is the pipeline value, the destination is configuration.

## Shape
Main input: `text`. Content in, the written `Path` out. Sibling: `WriteTextTo` (the path flows, the text is configuration).

## Changes the Disk
This action writes, copies, moves or deletes.
"""
