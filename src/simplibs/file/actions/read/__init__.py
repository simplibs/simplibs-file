from .ReadBytes import ReadBytes
from .ReadJson import ReadJson
from .ReadLines import ReadLines
from .ReadText import ReadText


_DESIGN_NOTES = """
# File Actions Read Sub-Package

## Purpose
Pipeline actions wrapping file reading functions (`read_bytes`, `read_text`,
`read_lines`, and `read_json`). These actions decode and load content into memory.

## Internal Components Registry

| Component   | Type   | Description                                               |
| :---------- | :----- | :-------------------------------------------------------- |
| `ReadBytes` | Action | Reads the full binary content of a file as bytes.         |
| `ReadJson`  | Action | Reads and parses a file's content as JSON.                |
| `ReadLines` | Action | Reads a file as a list of lines with exact endings.       |
| `ReadText`  | Action | Reads the full text of a file with normalized newlines.   |
"""