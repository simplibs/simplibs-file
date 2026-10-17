from simplibs.actions import create_action
# Outers
from ...logic.read import read_lines


ReadLines = create_action(
    read_lines,
    main_param="path",
    class_name="ReadLines",
)
"""Action wrapping `read_lines` — reads a file as a list of lines."""


_DESIGN_NOTES = """
# ReadLines — Action Over `read_lines`

## Purpose
`ReadLines(keep_ends=True)` when the original line endings must survive.

## Shape
Main input: `path`. Path in, `list[str]` out. For large files use `iter_lines` directly — a generator has no action (same reasoning as `iter_paths`).
"""
