from typing import Literal


NewlineMode = Literal["\n", "\r\n", "\r"] | None
"""The line ending a text write produces.

`"\\n"` (default of the library), `"\\r\\n"` (Windows), `"\\r"` (old Mac), or
`None` for the line ending of the current platform (`os.linesep`).
"""


_DESIGN_NOTES = """
# NewlineMode — Deterministic Line Endings

## Purpose
Python's text mode silently writes `\\r\\n` on Windows, so the same program
produces different bytes on different machines. The library defaults to
`"\\n"` and makes every other choice explicit.

## Same Meaning as `open(newline=...)` on Writes
Every `"\\n"` in the text becomes the chosen ending; an existing `"\\r\\n"` is
therefore not "recognized" and would become `"\\r\\r\\n"` — exactly what
`open()` does. Text with its own line endings should be written as bytes.

## `None` Is Explicit Platform Behaviour
Not the default — a caller has to ask for it.
"""
