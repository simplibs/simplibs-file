from simplibs.actions import create_action
# Outers
from ...logic.write import append_text


AppendText = create_action(
    append_text,
    main_param="text",
    class_name="AppendText",
)
"""Action wrapping `append_text` — appends the text flowing in to the configured `path`."""


_DESIGN_NOTES = """
# AppendText — Action Over `append_text`

## Purpose
A log-like output: every run adds what it produced.

## Shape
Main input: `text`. Content in, the target `Path` out. Default `use_draft=False` (see `append_text`). Sibling: `AppendTextTo`.

## Changes the Disk
This action writes, copies, moves or deletes.
"""
