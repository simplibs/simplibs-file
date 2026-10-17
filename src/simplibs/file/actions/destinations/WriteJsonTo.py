from simplibs.actions import create_action
# Outers
from ...logic.write import write_json


WriteJsonTo = create_action(
    write_json,
    main_param="path",
    class_name="WriteJsonTo",
)
"""Action wrapping `write_json` — writes the configured `data` as JSON to the path flowing in."""


_DESIGN_NOTES = """
# WriteJsonTo — Action Over `write_json`

## Purpose
The same JSON document (defaults, a skeleton) written to every path.

## Shape
Main input: `path`. Path in, the written `Path` out. Sibling of `WriteJson`.

## Changes the Disk
This action writes, copies, moves or deletes.
"""
