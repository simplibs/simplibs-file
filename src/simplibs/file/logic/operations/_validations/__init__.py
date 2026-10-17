from .raise_file_transfer_error import raise_file_transfer_error
from .raise_invalid_suffix_error import raise_invalid_suffix_error
from .raise_same_file_error import raise_same_file_error


_DESIGN_NOTES = """
# File Operations Diagnostic Helpers Sub-Package

## Purpose
Internal diagnostic validation routines raising structured exceptions specific
to file transfer and operation parameters.

## Internal Components Registry

| Component                   | Type     | Description                                                         |
| :-------------------------- | :------- | :------------------------------------------------------------------ |
| `raise_file_transfer_error` | Function | Raises `AccessError` when an OS error occurs during file transfers. |
| `raise_invalid_suffix_error`| Function | Raises `ParamError` when a suffix argument is malformed.            |
| `raise_same_file_error`     | Function | Raises `ParamError` when source and destination paths are identical.|
"""