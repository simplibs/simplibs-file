from .drop_redundant_bom import drop_redundant_bom
from .prepare_write_target import prepare_write_target
from .encode_text import encode_text


_DESIGN_NOTES = """
# File Write Internal Helpers Sub-Package

## Purpose
Internal helper routines supporting file writing, target preparation, and BOM management.

## Internal Components Registry

| Component             | Type     | Description                                                          |
| :-------------------- | :------- | :------------------------------------------------------------------- |
| `drop_redundant_bom`  | Function | Removes redundant byte-order marks when appending to non-empty files.|
| `prepare_write_target`| Function | Normalizes a write target, checks directory/overwrite, and ensures parent dir.|
| `encode_text`      | Function | Encodes text into bytes with line ending normalization.              |
"""