from simplibs.actions import create_action
# Outers
from ...logic.inspect import file_size


FileSize = create_action(
    file_size,
    main_param="path",
    class_name="FileSize",
)
"""Action wrapping `file_size` — measures the size of the file flowing in, in bytes."""


_DESIGN_NOTES = """
# FileSize — Action Over `file_size`

## Purpose
`... >> FileSize()` where a number is needed; for filtering prefer the `SizeIs` rule.

## Shape
Main input: `path`. Path in, `int` out.
"""
