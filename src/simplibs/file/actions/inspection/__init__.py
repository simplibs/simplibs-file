from .FileHash import FileHash
from .FileSize import FileSize


_DESIGN_NOTES = """
# File Actions Inspect Sub-Package

## Purpose
Pipeline actions wrapping inspection functions (`file_hash` and `file_size`).
These actions query file attributes without modifying the disk.

## Internal Components Registry

| Component  | Type   | Description                                               |
| :--------- | :----- | :-------------------------------------------------------- |
| `FileHash` | Action | Computes and returns the hash digest string of a file.    |
| `FileSize` | Action | Measures and returns the size of a file in bytes.         |
"""