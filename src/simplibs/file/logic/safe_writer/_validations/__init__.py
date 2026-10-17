from .raise_safe_writer_commit_error import raise_safe_writer_commit_error
from .raise_safe_writer_draft_create_error import raise_safe_writer_draft_create_error
from .raise_safe_writer_draft_open_error import raise_safe_writer_draft_open_error


_DESIGN_NOTES = """
# File Safe Writer Diagnostic Helpers Sub-Package

## Purpose
Internal diagnostic validation routines raising structured `AccessError` exceptions
for safe writer failures (draft creation, opening, and committing).

## Internal Components Registry

| Component                            | Type     | Description                                                           |
| :----------------------------------- | :------- | :-------------------------------------------------------------------- |
| `raise_safe_writer_commit_error`     | Function | Raises `AccessError` when a finished draft cannot replace target.     |
| `raise_safe_writer_draft_create_error`| Function | Raises `AccessError` when a draft file cannot be created.            |
| `raise_safe_writer_draft_open_error`  | Function | Raises `AccessError` when a created draft cannot be opened.           |
"""