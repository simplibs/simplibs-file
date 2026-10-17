from .raise_decode_error import raise_decode_error
from .raise_json_decode_error import raise_json_decode_error


_DESIGN_NOTES = """
# File Read Diagnostic Helpers Sub-Package

## Purpose
Internal diagnostic validation routines raising structured conversion exceptions
for text decoding and JSON parsing errors.

## Internal Components Registry

| Component                | Type     | Description                                                           |
| :----------------------- | :------- | :-------------------------------------------------------------------- |
| `raise_decode_error`     | Function | Raises `ConversionError` when byte data cannot be decoded as text.    |
| `raise_json_decode_error`| Function | Raises `ConversionError` when file content is not valid JSON.         |
"""