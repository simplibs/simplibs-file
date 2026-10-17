from simplibs.actions import create_action
# Outers
from ...logic.inspect import file_hash


FileHash = create_action(
    file_hash,
    main_param="path",
    class_name="FileHash",
)
"""Action wrapping `file_hash` — hashes the content of the file flowing in."""


_DESIGN_NOTES = """
# FileHash — Action Over `file_hash`

## Purpose
Change detection: `... >> FileHash(algorithm="sha256")`.

## Shape
Main input: `path`. Path in, a hex digest `str` out.
"""
