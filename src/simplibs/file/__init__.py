from .logic.inspection import (
    file_hash,
    file_size,
    is_text_file,
)
from .logic.operations import (
    backup_file,
    copy_file,
    delete_file,
    move_file,
    rename_file,
)
from .logic.read import (
    iter_lines,
    read_bytes,
    read_json,
    read_lines,
    read_text,
)
from .logic.safe_writer import (
    IGNORE_DRAFTS,
    SafeFileWriter,
)
from .logic.write import (
    append_bytes,
    append_text,
    write_aggregated,
    write_bytes,
    write_json,
    write_lines,
    write_text,
)
from .annotations import (
    ByteCount,
    EncodingErrors,
    EncodingName,
    HashAlgorithm,
    NewlineMode,
    TextCollection,
    WriterMode,
)

__all__ = [
    # read — a file in, its content out
    "read_bytes",
    "read_text",
    "read_lines",
    "iter_lines",
    "read_json",
    # write — content in, a file out
    "write_bytes",
    "append_bytes",
    "write_text",
    "append_text",
    "write_lines",
    "write_aggregated",
    "write_json",
    # operations — do something TO a file
    "copy_file",
    "move_file",
    "rename_file",
    "delete_file",
    "backup_file",
    # inspect — ask a file about itself
    "file_size",
    "file_hash",
    "is_text_file",
    # safe writing
    "SafeFileWriter",
    "IGNORE_DRAFTS",
    # annotations — types for your own signatures
    "ByteCount",
    "EncodingErrors",
    "EncodingName",
    "HashAlgorithm",
    "NewlineMode",
    "TextCollection",
    "WriterMode",
]


_DESIGN_NOTES = """
# simplibs-file — Package Root

## Purpose
Safe, composable work with the CONTENT of files: read, write, copy, move,
delete, back up and inspect — as plain functions, as `Rule`s, and as pipeline
`Action`s. The sister of `simplibs-path`, which handles the paths themselves.

## What the Root Exports
Everything from the `logic/` sub-packages (`read`, `write`, `operations`,
`inspect`, `safe_writer`) and the public annotations:

    from simplibs.file import read_text, write_json, SafeFileWriter, EncodingName

## What the Root Deliberately Does NOT Export
* **`rules/` and `actions/`** — domain folders with their own `__all__`,
  imported through their domain, exactly as in `simplibs-path`:

      from simplibs.file.rules import IsTextFile, SizeIs, ContentIs
      from simplibs.file.actions import ReadText, WriteText

  Rules and actions are different kinds of thing and should stay visibly
  different at the import line.
* **Internals** — `_helpers/`, `_validations/` and the `_helpers/` of each domain.

## Why the Annotations ARE Exported
`EncodingName`, `EncodingErrors`, `NewlineMode`, `HashAlgorithm`, `ByteCount`,
`TextCollection` and `WriterMode` are meant for the caller's own signatures, always used with the
functions. `PathLike` is not redefined here — it comes from `simplibs.path`.

## `__all__`
Defined here and in the domain folders (`rules`, `actions`) only; the
sub-packages below export by plain imports.

## Internal Components Registry (Root Exports)

| Component       | Type           | Description                                                     |
| :-------------- | :------------- | :-------------------------------------------------------------- |
| `read_bytes`    | Function       | Reads the full binary content of a file.                        |
| `read_text`     | Function       | Reads the full text of a file with normalized newlines.         |
| `read_lines`    | Function       | Reads a file as a list of lines with exact endings.             |
| `iter_lines`    | Function       | Streams lines of a file lazily without loading it whole.        |
| `read_json`     | Function       | Reads a file and parses its content as JSON.                    |
| `write_bytes`   | Function       | Writes raw bytes to a file (core writer).                       |
| `append_bytes`  | Function       | Appends raw bytes to a file.                                    |
| `write_text`    | Function       | Encodes text in memory and writes it to a file.                 |
| `append_text`   | Function       | Appends text to a file with encoding/BOM handling.              |
| `write_lines`   | Function       | Writes a collection of lines to a file, one per line.           |
| `write_aggregated`| Function     | Joins text fragments with a separator and writes them as one.   |
| `write_json`    | Function       | Serializes a value to JSON and writes it to a file.             |
| `copy_file`     | Function       | Copies a file preserving permissions and timestamps.            |
| `move_file`     | Function       | Moves or renames a file (across folders/devices).               |
| `rename_file`   | Function       | Backward-compatible alias for `move_file`.                      |
| `delete_file`   | Function       | Deletes a file or symlink (never its target).                   |
| `backup_file`   | Function       | Creates an atomic backup copy next to the file.                 |
| `file_size`     | Function       | Measures the size of a regular file in bytes.                   |
| `file_hash`     | Function       | Computes a fixed-length hash digest of file content.            |
| `is_text_file`  | Function       | Checks whether a file's beginning looks like text.              |
| `SafeFileWriter`| Class          | Context manager for crash-safe writing via draft-and-swap.      |
| `IGNORE_DRAFTS` | Constant (Set) | Scanner pattern for matching temporary leftover draft files.    |
| `ByteCount`     | Annotated Type | A validated positive integer representing a number of bytes.    |
| `EncodingErrors`| Literal Type   | Allowed encoding error handling strategies for read/write.      |
| `EncodingName`  | Annotated Type | A validated string representing a valid Python text encoding.   |
| `HashAlgorithm` | Literal Type   | Guaranteed fixed-length hash algorithms from `hashlib`.         |
| `NewlineMode`   | Literal / None | Deterministic line ending modes for text writing.               |
| `TextCollection`| Annotated Type | A collection of texts (lines, fragments) — never a bare string. |
| `WriterMode`    | Literal Type   | Supported open modes for `SafeFileWriter` (`w`, `wb`, `a`, `ab`).|
"""