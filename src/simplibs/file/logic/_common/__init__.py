_DESIGN_NOTES = """
# File Common Logic Sub-Package

## Purpose
Groups shared internal helper functions and diagnostic validation routines
used across the file logic sub-packages.

## Internal Components Registry

| Sub-package   | Kind                     | What it holds                                                 |
| :------------ | :----------------------- | :------------------------------------------------------------ |
| `helpers`     | Shared internal helpers  | `resolve_source_file` — shared path resolution and validation helper. |
| `validations` | Diagnostic helpers       | Structured exception raisers (`raise_destination_exists_error`, `raise_file_not_found_error`, etc.). |
"""