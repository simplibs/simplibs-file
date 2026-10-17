from .is_byte_count import is_byte_count
from .is_text_encoding import is_text_encoding


_DESIGN_NOTES = """
# annotations/_helpers — Private Helpers of the Annotations

Plain imports only. Used by the annotations of this folder, not exported
from the package root.

## Internal Components Registry

| Component          | Type     | Description                                                     |
| :----------------  | :------- | :-------------------------------------------------------------- |
| `is_byte_count`    | Function | Validates whether a value is a positive integer number of bytes.|
| `is_text_encoding` | Function | Validates whether a name is a working text encoding in Python.  |
"""