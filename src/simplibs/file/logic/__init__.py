_DESIGN_NOTES = """
# File Logic Package

## Purpose
The functional core of `simplibs-file`: plain, reusable functions and classes
that work on their own, grouped by responsibility. The sub-packages handle
internal shared routines, file inspection, disk operations, reading, writing,
and crash-safe operations.

This package groups; it does not export. It has no imports of its own, so
importing it costs nothing and creates no import cycles. The main package
`__init__` (`simplibs.file`) reaches into the sub-packages below and
propagates their public names.

## Internal Components Registry

| Sub-package   | Kind                   | What it holds                                                                                   |
| :------------ | :--------------------- | :---------------------------------------------------------------------------------------------- |
| `_common`     | Shared internal logic  | Shared internal helpers (`resolve_source_file`, `encode_text`, `replace_with_retry`) and structured validation raisers. |
| `inspect`     | File metadata queries  | `file_size`, `file_hash`, and `is_text_file` — checking file attributes without modifying content. |
| `operations`  | File manipulations     | `copy_file`, `move_file` (with `rename_file` alias), `delete_file`, and `backup_file`.          |
| `read`        | Content reading        | `read_bytes`, `read_text`, `read_lines`, `read_json`, and `iter_lines` (lazy stream).           |
| `safe_writer` | Crash-safe mechanism   | `SafeFileWriter` context manager and `IGNORE_DRAFTS` pattern for atomic draft-and-swap writing.   |
| `write`       | Content writing        | `write_bytes`, `write_text`, `write_lines`, `write_aggregated`, `write_json`, and appenders.     |

## Layering & Design
- `logic` serves as the private implementation engine of the file library.
- Higher-level abstractions (like rules or actions, if applicable) build on top of these primitives.
- Sub-packages depend on `_common` for shared validation and helper routines while avoiding circular imports.
"""