from .decode_bytes import decode_bytes
from .stream_lines import stream_lines
from .strip_line_ending import strip_line_ending


_DESIGN_NOTES = """
# File Read Internal Helpers Sub-Package

## Purpose
Internal helper routines supporting file reading, decoding, and line streaming
operations.

## Internal Components Registry

| Component          | Type     | Description                                                          |
| :----------------- | :------- | :------------------------------------------------------------------- |
| `decode_bytes`     | Function | Decodes raw bytes into text in memory with error handling.           |
| `stream_lines`     | Function | Lazily yields lines of a verified file one at a time.                |
| `strip_line_ending`| Function | Removes exactly one trailing line ending from a line string.         |
"""