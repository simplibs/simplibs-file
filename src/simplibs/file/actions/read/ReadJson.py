from simplibs.actions import create_action
# Outers
from ...logic.read import read_json


ReadJson = create_action(
    read_json,
    main_param="path",
    class_name="ReadJson",
)
"""Action wrapping `read_json` — reads and parses a JSON file."""


_DESIGN_NOTES = """
# ReadJson — Action Over `read_json`

## Purpose
`ReadJson()` turns a config or manifest file into data inside a pipeline.

## Shape
Main input: `path`. Path in, the parsed value out. BOM-tolerant; a syntax error is a card with line and column.
"""
