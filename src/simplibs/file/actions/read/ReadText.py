from simplibs.actions import create_action
# Outers
from ...logic.read import read_text


ReadText = create_action(
    read_text,
    main_param="path",
    class_name="ReadText",
)
"""Action wrapping `read_text` — reads a file as text (BOM-tolerant, line endings normalized to `\n`)."""


_DESIGN_NOTES = """
# ReadText — Action Over `read_text`

## Purpose
`CollectFiles(...) >> ForEach(ReadText())` — the usual way text enters a pipeline.

## Shape
Main input: `path`. Options: `encoding` (default `utf-8-sig`) and `errors`. Path in, `str` out.
"""
