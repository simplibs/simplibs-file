from simplibs.actions import create_action
# Outers
from ...logic.read import read_bytes


ReadBytes = create_action(
    read_bytes,
    main_param="path",
    class_name="ReadBytes",
)
"""Action wrapping `read_bytes` — reads the whole content of a file as bytes."""


_DESIGN_NOTES = """
# ReadBytes — Action Over `read_bytes`

## Purpose
`ReadBytes()` as the first step of a pipeline that works on raw data (hashing, binary parsing).

## Shape
Main input: `path`. Path in, `bytes` out.
"""
