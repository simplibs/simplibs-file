from simplibs.actions import create_action
# Outers
from ...logic.write import write_json


WriteJson = create_action(
    write_json,
    main_param="data",
    class_name="WriteJson",
)
"""Action wrapping `write_json` — serializes the value flowing in to JSON and writes it to the configured `path`."""


_DESIGN_NOTES = """
# WriteJson — Action Over `write_json`

## Purpose
`... >> WriteJson(path="out/index.json", sort_keys=True)`.

## Shape
Main input: `data`. Any JSON-compatible value in, the written `Path` out. Sibling: `WriteJsonTo`.

## Changes the Disk
This action writes, copies, moves or deletes.
"""
