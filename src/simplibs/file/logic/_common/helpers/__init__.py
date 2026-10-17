from .replace_with_retry import replace_with_retry
from .resolve_source_file import resolve_source_file
from .commit_draft import commit_draft
from .create_draft import create_draft
from .delete_draft import delete_draft

_DESIGN_NOTES = """
# File Common Internal Helpers Sub-Package

## Purpose
Shared helper functions used internally across file operations, including
draft management and atomic file replacement.

## Internal Components Registry

| Component             | Type     | Description                                                          |
| :-------------------- | :------- | :------------------------------------------------------------------- |
| `replace_with_retry`  | Function | Atomically replaces destination with source, retrying Windows locks. |
| `resolve_source_file` | Function | Normalizes a path and guarantees it points to an existing file.     |
| `commit_draft`        | Function | Atomically replaces target with draft, handling locks and sync.      |
| `create_draft`        | Function | Creates a unique, empty draft file next to the target.               |
| `delete_draft`        | Function | Discards a draft file quietly without throwing errors.               |
"""