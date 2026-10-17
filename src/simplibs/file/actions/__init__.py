from .inspection.FileHash import FileHash
from .inspection.FileSize import FileSize
from .operations.BackupFile import BackupFile
from .operations.CopyFile import CopyFile
from .operations.CopyFileFrom import CopyFileFrom
from .operations.DeleteFile import DeleteFile
from .operations.MoveFile import MoveFile
from .operations.RenameFile import RenameFile
from .read.ReadBytes import ReadBytes
from .read.ReadJson import ReadJson
from .read.ReadLines import ReadLines
from .read.ReadText import ReadText
from .write.AppendBytes import AppendBytes
from .write.AppendText import AppendText
from .write.WriteAggregated import WriteAggregated
from .write.WriteBytes import WriteBytes
from .write.WriteJson import WriteJson
from .write.WriteLines import WriteLines
from .write.WriteText import WriteText
from .destinations.AppendBytesTo import AppendBytesTo
from .destinations.AppendTextTo import AppendTextTo
from .destinations.WriteAggregatedTo import WriteAggregatedTo
from .destinations.WriteBytesTo import WriteBytesTo
from .destinations.WriteJsonTo import WriteJsonTo
from .destinations.WriteLinesTo import WriteLinesTo
from .destinations.WriteTextTo import WriteTextTo


__all__ = [
    # read — path in, content out
    "ReadBytes",
    "ReadText",
    "ReadLines",
    "ReadJson",
    # write (content flows in; the path is configuration)
    "WriteBytes",
    "AppendBytes",
    "WriteText",
    "AppendText",
    "WriteLines",
    "WriteAggregated",
    "WriteJson",
    # write, the other way round (the path flows in; the content is configuration)
    "WriteBytesTo",
    "AppendBytesTo",
    "WriteTextTo",
    "AppendTextTo",
    "WriteLinesTo",
    "WriteAggregatedTo",
    "WriteJsonTo",
    # operations — things you do TO a file
    "CopyFile",
    "CopyFileFrom",
    "MoveFile",
    "RenameFile",
    "DeleteFile",
    "BackupFile",
    # inspect — ask a file about itself
    "FileSize",
    "FileHash",
]


_DESIGN_NOTES = """
# File Actions Sub-Package

## Purpose
The functions of the library that take one main value and return one result,
as `Action`s: constructed once with their options, then called with the main
input and chainable with `>>`, `&` and `|`.

```python
pipeline = (
    IsFile() & IsTextFile()                   # Rules — they become guard steps
    >> ReadText()
    >> some_transformation
    >> WriteText(path="out/result.txt")
)

```

## Two Directions for Writers

A writer needs a path AND a content, and a pipeline carries one value. Both
choices are offered, named so they read naturally:

* `WriteText(path=...)("content")` — the CONTENT flows, the path is configuration.
The usual case: `ReadText() >> transform >> WriteText(path=...)`, and the only
one that fits `WriteAggregated` (a list of texts in, one file out).
* `WriteTextTo(text=...)("path")` — the PATH flows, the content is configuration.
For "the same content to every path of a list".
`CopyFile(destination=...)(source)` and `CopyFileFrom(source=...)(destination)`
follow the same idea. A pipeline whose every item carries its own path AND its
own content composes the two with ordinary functions; that is the extractor's job.

## What Is Not Here

* **Predicates and rules:** `is_text_file` has no action — `IsTextFile()` is a Rule
and already works as a pipeline step (a pass-through guard).
* **`iter_lines`:** a generator does not fit one-value-in, one-value-out.
* **`SafeFileWriter`:** a context manager, not a function from value to value.
* **A reversed `MoveFile`:** no realistic use.

## Logging

All actions use the default logging of `create_action`; long values are shortened
by the logging layer itself, so file content does not flood the log.

## Async

All are synchronous actions, so `await action.acall(data)` runs them in a worker
thread — the right model for blocking file I/O.

## Domain Folder: `__all__`

Like `rules/`, this package defines `__all__` (the public actions).

## Internal Components Registry

| Component           | Type   | Description                                                   |
|---------------------|--------|---------------------------------------------------------------|
| `ReadBytes`         | Action | Reads full binary content of a file as bytes.                 |
| `ReadText`          | Action | Reads full text of a file with normalized newlines.           |
| `ReadLines`         | Action | Reads a file as a list of lines.                              |
| `ReadJson`          | Action | Reads and parses a file as JSON.                              |
| `WriteBytes`        | Action | Writes incoming bytes to a configured path.                   |
| `AppendBytes`       | Action | Appends incoming bytes to a configured path.                  |
| `WriteText`         | Action | Writes incoming text to a configured path.                    |
| `AppendText`        | Action | Appends incoming text to a configured path.                   |
| `WriteLines`        | Action | Writes incoming lines to a configured path.                   |
| `WriteAggregated`   | Action | Joins incoming text fragments and writes them to a path.      |
| `WriteJson`         | Action | Serializes incoming data to JSON and writes it to a path.     |
| `WriteBytesTo`      | Action | Writes configured bytes to the incoming path.                 |
| `AppendBytesTo`     | Action | Appends configured bytes to the incoming path.                |
| `WriteTextTo`       | Action | Writes configured text to the incoming path.                  |
| `AppendTextTo`      | Action | Appends configured text to the incoming path.                 |
| `WriteLinesTo`      | Action | Writes configured lines to the incoming path.                 |
| `WriteAggregatedTo` | Action | Writes configured joined text fragments to the incoming path. |
| `WriteJsonTo`       | Action | Writes configured JSON data to the incoming path.             |
| `CopyFile`          | Action | Copies input file to the configured destination.              |
| `CopyFileFrom`      | Action | Copies configured source file to the input destination.       |
| `MoveFile`          | Action | Moves or renames the input file to the destination.           |
| `RenameFile`        | Action | Backward-compatible alias action wrapping `move_file`.        |
| `DeleteFile`        | Action | Deletes the file or symlink entry flowing in.                 |
| `BackupFile`        | Action | Creates an atomic backup copy next to the input file.         |
| `FileSize`          | Action | Measures and returns the size of a file in bytes.             |
| `FileHash`          | Action | Computes and returns the hash digest string of a file.        |
"""