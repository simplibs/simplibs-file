from .raise_json_encode_error import raise_json_encode_error
from .raise_encode_error import raise_encode_error


_DESIGN_NOTES = """
# File Write Diagnostic Helpers Sub-Package

## Purpose
Internal diagnostic validation routines raising structured conversion exceptions
for JSON serialization errors during writing.

## Internal Components Registry

| Component                | Type     | Description                                                           |
| :----------------------- | :------- | :-------------------------------------------------------------------- |
| `raise_json_encode_error`| Function | Raises `ConversionError` when data cannot be serialized to JSON.      |
| `raise_encode_error`     | Function | Raises `ConversionError` when text contains unencodable characters.   |
"""