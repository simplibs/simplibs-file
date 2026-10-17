# 📄 `simplibs-file`

[![PyPI](https://img.shields.io/pypi/v/simplibs-file)](https://pypi.org/project/simplibs-file/)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![Licence](https://img.shields.io/badge/licence-MIT-green)](https://github.com/simplibs/simplibs-file/blob/main/LICENSE)

**Files you can trust — read, write, copy and inspect, without surprises.**

A Python library for everyday work with the **content of files**, built around one idea:
every operation exists first as a plain, well-behaved **function**, and is then offered as
a composable **`Rule`** (for filters and validation) and as a pipeline **`Action`** (for
chained processing). Writes are atomic by default, text is encoded *before* the disk is
touched, defaults are deterministic (UTF-8, `"\n"`, BOM-tolerant reading), and operations that
fail explain exactly why through structured
[`simplibs-exception`](https://pypi.org/project/simplibs-exception/) cards instead of leaking
a bare `OSError` or `UnicodeDecodeError`.

```python
from simplibs.file import read_json, write_json, copy_file

settings = read_json("config.json")                        # a BOM-tolerant read, a card on a syntax error
write_json("out/index.json", {"files": 3}, sort_keys=True) # serialized first, then swapped in atomically
copy_file("report.txt", "backup/report.txt")               # atomic, keeps permissions and times
```

> `simplibs-file` is the sister of
> [`simplibs-path`](https://pypi.org/project/simplibs-path/): that library works with the
> **paths** themselves (normalize, check, scan), this one with what is **inside** the files at
> those paths. Together they are the building blocks of file-processing pipelines. You can use
> the plain functions without ever touching rules or actions.

---

## 🧭 The Core Philosophy

File handling in Python is easy until it is not: `Path.write_text` truncates the file *before*
it encodes, so one unencodable character leaves a half-written file; a crash in the middle of
`shutil.copy2` leaves a truncated "backup" that looks real; `os.replace` between two disks
fails; `json.load` chokes on a BOM written by a Windows tool; deleting a symlink deletes the
file it points to; and the platform quietly decides your line endings. `simplibs-file` takes
those traps seriously:

* **Functions first.** All logic lives in small, independent, reusable functions. Rules and
  actions are thin layers over them — never a second copy of the logic.
* **Safe by default.** A write goes into a private draft that replaces the target in one
  atomic step, so an interruption leaves the old file or the new one, never half of each. A
  copy and a backup work the same way.
* **Encode first, touch the disk later.** Every text and JSON writer converts to bytes in
  memory; a bad character or an unserializable value fails with the target still intact.
* **Deterministic defaults.** Reads tolerate a BOM (`utf-8-sig`), writes are BOM-free `utf-8`
  with `"\n"` line endings — the same bytes on every machine. Anything else is an explicit choice.
* **Operations explain themselves.** Every failure is a structured, actionable card
  (`NotFoundError`, `StateError`, `AlreadyExistsError`, `ConversionError`, `AccessError`, ...)
  that names the file — or both files — and what the OS reported.
* **Entry or content, by intent.** Copying and backing up work on the **content** behind a
  symlink; moving and deleting work on the directory **entry**, so `delete_file("link")` removes
  the link and never the file it points to.
* **Honest about time.** A filesystem answer is true *now*; the docs say where a check is a
  fail-fast message rather than a guarantee.

---

## 📦 Installation

```bash
pip install simplibs-file
```

---

## 🚀 Quick Start in 60 Seconds

### Level 1: Plain functions

```python
from simplibs.file import read_text, write_text, append_text, read_lines

text = read_text("notes.txt")                       # the whole file, "\n" line endings
write_text("out/notes.txt", text.upper())           # the folder is created; the write is atomic
append_text("logs/run.log", "finished\n")           # creates the file if it is missing
lines = read_lines("notes.txt", keep_ends=True)     # every line keeps its original ending
```

### Level 2: Rules as filters and gates

```python
from simplibs.path import collect_files
from simplibs.path.rules import HasSuffix, IsFile
from simplibs.file.rules import ContentIs, IsTextFile, SizeIs
from simplibs.rules.predicates.comparisons import GreaterThan
from simplibs.rules.predicates.strings import StartsWith

extractable = IsFile() & HasSuffix(".py") & IsTextFile() & SizeIs(GreaterThan(0))
collect_files("~/project", include_filter=extractable)

extractable.describe()      # -> "existing file & suffix '.py' & text file & size: > 0"
ContentIs(StartsWith("#!")).is_valid("scripts/run.sh")     # -> True
```

### Level 3: Actions as pipeline steps

```python
from simplibs.actions import ForEach
from simplibs.path.actions import CollectFiles
from simplibs.path.rules import HasSuffix
from simplibs.file.actions import ReadText, WriteAggregated
from simplibs.file.rules import IsTextFile

merge_notes = (
    CollectFiles(include_filter=HasSuffix(".md") & IsTextFile())   # root folder -> list of paths
    >> ForEach(ReadText())                                         # paths       -> list of texts
    >> WriteAggregated(path="build/all_notes.md")                  # texts       -> the written Path
)

merge_notes("notes")                  # -> Path('<cwd>/build/all_notes.md')
await merge_notes.acall("notes")      # the same, off the event loop
```

### Level 4: Safety helpers

```python
from simplibs.file import SafeFileWriter, backup_file, file_hash, move_file

backup_file("report.txt")                    # -> report_20261013_142530.txt.bak — never overwritten
move_file("report.txt", "G:/archive/report.txt")   # also across devices
file_hash("archive.zip")                     # -> 'b5bb9d80...' — read in chunks, flat memory

with SafeFileWriter("out/data.json") as handle:    # crash-safe, for writes made in several steps
    handle.write('{"ok": true}')
```

---

## 🛠️ Architecture & Package Structure

```
src/simplibs/file/
├── logic/                ◄── The functional core — plain functions, no Rule/Action knowledge
│   ├── read/             ◄── read_bytes, read_text, read_lines, iter_lines, read_json
│   ├── write/            ◄── write_bytes, append_bytes, write_text, append_text, write_lines, write_aggregated, write_json
│   ├── operations/       ◄── copy_file, move_file, rename_file, delete_file, backup_file
│   ├── inspect/          ◄── file_size, file_hash, is_text_file
│   ├── safe_writer/      ◄── SafeFileWriter, IGNORE_DRAFTS
│   └── _common/          ◄── Internal helpers shared by the packages above
├── rules/                ◄── Rule classes over files (domain folder) — IsTextFile, SizeIs, ContentIs
├── actions/              ◄── Action classes over the functions (domain folder)
│   ├── read/  write/  destinations/  operations/  inspect/
└── annotations/          ◄── Shared types — EncodingName, EncodingErrors, NewlineMode, ByteCount, HashAlgorithm, WriterMode
```

Everything in `logic/` and the six public types is importable straight from `simplibs.file`.
`rules` and `actions` are separate domains, imported through their own folders:

```python
from simplibs.file import read_text, write_json, SafeFileWriter, EncodingName    # functions and types
from simplibs.file.rules import IsTextFile, SizeIs, ContentIs                    # rules
from simplibs.file.actions import ReadText, WriteText                            # actions
```

`PathLike` is not redefined here — it comes from
[`simplibs.path`](https://pypi.org/project/simplibs-path/).

---

## 📖 `logic/read/` — Everything that reads content

All read a regular file (a symlink is followed), never change anything, and report a missing
file, undecodable bytes or broken JSON as a card. Text readers default to `"utf-8-sig"`, so a
BOM never spoils the result.

| Function      | Description / Parameters                                                                                       |
|---------------|----------------------------------------------------------------------------------------------------------------|
| `read_bytes`  | The raw content — the core every other reader is built on (`path`).                                            |
| `read_text`   | The whole text, line endings normalized to `"\n"` (`path`, `encoding="utf-8-sig"`, `errors="strict"`).         |
| `read_lines`  | A list of lines (`path`, `encoding`, `errors`, `keep_ends=False`). Only `\n`, `\r\n` and `\r` end a line.      |
| `iter_lines`  | The lazy counterpart of `read_lines` — one line at a time, flat memory (same parameters).                      |
| `read_json`   | Reads and parses JSON; a syntax error carries the line and column (`path`, `encoding`, `errors`).              |

➡️ [README_FILE_READ](https://github.com/simplibs/simplibs-file/blob/main/docs/logic/README_FILE_READ.md)

---

## 📝 `logic/write/` — Everything that writes content

The functions that change the disk. Each returns the normalized target `Path`, so it chains.
Text is encoded in memory first; the target's folder is created when missing.

| Function           | Description / Parameters                                                                                                 |
|--------------------|--------------------------------------------------------------------------------------------------------------------------|
| `write_bytes`      | The first core writer (`path`, `data`, `overwrite=True`, `use_draft=True`, `sync=False`).                                |
| `append_bytes`     | The second core writer — adds to a file, creating it if missing (`path`, `data`, `use_draft=False`, `sync=False`).       |
| `write_text`       | Encodes and writes text (`path`, `text`, `encoding="utf-8"`, `errors`, `newline="\n"`, `overwrite`, `use_draft`, `sync`). |
| `append_text`      | Appends text; a BOM is never written into the middle of a file (`path`, `text`, `encoding`, `errors`, `newline`, `use_draft=False`, `sync`). |
| `write_lines`      | One item per line (`path`, `lines`, ..., `trailing_newline=True`).                                                       |
| `write_aggregated` | Joins fragments with a separator and writes them as one file (`path`, `parts`, `separator="\n"`, ..., `trailing_newline=False`). |
| `write_json`       | Serializes first, then writes (`path`, `data`, `indent=2`, `ensure_ascii=False`, `sort_keys`, `allow_nan=False`, `default`, `trailing_newline=True`, ...). |

➡️ [README_FILE_WRITE](https://github.com/simplibs/simplibs-file/blob/main/docs/logic/README_FILE_WRITE.md)

---

## 📦 `logic/operations/` — Work with the file itself

All change the disk and return the normalized path of the result. Copies, backups and
cross-device moves are atomic — complete, or not there.

| Function      | Description / Parameters                                                                                              |
|---------------|-----------------------------------------------------------------------------------------------------------------------|
| `copy_file`   | Atomic copy keeping permissions and times (`source`, `destination`, `overwrite=False`, `sync=False`). The destination is a **file** path, never a folder. |
| `move_file`   | Moves or renames — across folders **and devices**; a symlink is moved as a link (`source`, `destination`, `overwrite=False`). |
| `rename_file` | The old name of `move_file` — the very same function.                                                                 |
| `delete_file` | Deletes a file or a symlink, never the link's target (`path`, `missing_ok=False`, `force=False`).                     |
| `backup_file` | A backup next to the file, never overwriting an older one (`path`, `suffix=".bak"`, `timestamp=True`, `sync=False`).  |

➡️ [README_FILE_OPERATIONS](https://github.com/simplibs/simplibs-file/blob/main/docs/logic/README_FILE_OPERATIONS.md)

---

## 🔎 `logic/inspect/` — Ask a file about itself

None of them changes anything. `file_size` and `file_hash` are strict (a card when there is no
file); `is_text_file` is a predicate that returns `False` instead.

| Function       | Description / Parameters                                                                                           |
|----------------|--------------------------------------------------------------------------------------------------------------------|
| `file_size`    | The size in bytes, from one `stat` (`path`).                                                                       |
| `file_hash`    | The hex digest of the content, read in chunks (`path`, `algorithm="sha256"`, `chunk_size=1_048_576`).              |
| `is_text_file` | Whether the beginning looks like text — decodes and contains no NUL (`path`, `sample_size=8192`, `encoding="utf-8"`). |

➡️ [README_FILE_INSPECT](https://github.com/simplibs/simplibs-file/blob/main/docs/logic/README_FILE_INSPECT.md)

---

## 🔐 `logic/safe_writer/` — Crash-safe writing

The one place that knows how to replace a file safely. Every writer goes through it unless you
opt out with `use_draft=False`; use it directly when a file is written in several steps.

| Component        | Description / Parameters                                                                                              |
|------------------|-----------------------------------------------------------------------------------------------------------------------|
| `SafeFileWriter` | A context manager: writes go into a draft that replaces the target only when the block ends without an exception (`target_path`, `mode="w"`, `encoding`, `errors`, `newline`, `sync`). |
| `IGNORE_DRAFTS`  | A scanner `ignore_names` pattern for leftover drafts — opt-in: `DEFAULT_IGNORE_NAMES \| IGNORE_DRAFTS`.               |

➡️ [README_FILE_SAFE_WRITER](https://github.com/simplibs/simplibs-file/blob/main/docs/logic/README_FILE_SAFE_WRITER.md)

---

## 📐 `rules/` — Rules for files

Every rule is a `Rule` from [`simplibs-rules`](https://pypi.org/project/simplibs-rules/):
composable with `&`, `|` and `~`, usable as a scanner filter, as a `@validate_call` annotation
(`validated_type(Path, IsTextFile())`) and as a pipeline gate (`IsTextFile() >> ReadText()`).
They never raise for disk problems — a missing file, a directory or undecodable bytes simply fail
the rule. Questions about the **path** itself (`IsFile`, `HasSuffix`, `NameIs`, ...) live in
[`simplibs.path.rules`](https://pypi.org/project/simplibs-path/).

| Class        | Description / Parameters                                                                                   |
|--------------|------------------------------------------------------------------------------------------------------------|
| `IsTextFile` | A readable file whose beginning looks like text (`sample_size=8192`, `encoding="utf-8"`).                  |
| `SizeIs`     | The size in bytes satisfies another rule (`rule`) — `SizeIs(GreaterThan(0))`, `SizeIs(InRange(1, 1024))`.  |
| `ContentIs`  | The beginning of the text satisfies another rule (`rule`, `encoding="utf-8-sig"`, `max_bytes=65_536`) — `ContentIs(StartsWith("#!"))`. |

➡️ [README_FILE_RULES](https://github.com/simplibs/simplibs-file/blob/main/docs/README_FILE_RULES.md)

---

## ⚙️ `actions/` — Pipeline steps

Every function that takes one main value and returns one result is also an `Action` from
[`simplibs-actions`](https://pypi.org/project/simplibs-actions/): configured once, called with
the main input, chainable with `>>`, `&` and `|`, and awaitable through `acall`.

A writer needs a path **and** a content, but a pipeline carries one value — so both directions
are offered: `WriteText(path=...)("content")` (the **content** flows) and
`WriteTextTo(text=...)("path")` (the **path** flows).

| Group           | Actions                                                                                                      | Main input → result                |
|-----------------|--------------------------------------------------------------------------------------------------------------|------------------------------------|
| **read**        | `ReadBytes`, `ReadText`, `ReadLines`, `ReadJson`                                                             | path → `bytes` / `str` / `list[str]` / value |
| **write**       | `WriteBytes`, `AppendBytes`, `WriteText`, `AppendText`, `WriteLines`, `WriteAggregated`, `WriteJson`         | content → written `Path`           |
| **destinations**| `WriteBytesTo`, `AppendBytesTo`, `WriteTextTo`, `AppendTextTo`, `WriteLinesTo`, `WriteAggregatedTo`, `WriteJsonTo` | path → written `Path`        |
| **operations**  | `CopyFile`, `CopyFileFrom`, `MoveFile`, `RenameFile`, `DeleteFile`, `BackupFile`                             | path → result `Path`               |
| **inspect**     | `FileSize`, `FileHash`                                                                                       | path → `int` / `str`               |

Predicates, `iter_lines` and `SafeFileWriter` have no action: a `Rule` is already a valid
pipeline step (it becomes a pass-through gate), and a generator or a context manager does not
fit a one-value-in, one-value-out model.

➡️ [README_FILE_ACTIONS](https://github.com/simplibs/simplibs-file/blob/main/docs/README_FILE_ACTIONS.md)

---

## 🏷️ `annotations/` — Shared validatable annotations

| Type             | Description                                                                                          |
|------------------|------------------------------------------------------------------------------------------------------|
| `EncodingName`   | The name of a text encoding Python can both encode and decode with. Rejects `"rot13"`, `"base64"`, unknown names. |
| `EncodingErrors` | `"strict"`, `"ignore"`, `"replace"`, `"backslashreplace"`, `"surrogateescape"`, `"surrogatepass"` — the handlers that work in both directions. |
| `NewlineMode`    | `"\n"`, `"\r\n"`, `"\r"` or `None` for the platform's own line ending.                               |
| `ByteCount`      | A positive number of bytes (a chunk, a sample). Rejects zero, negatives and `bool`.                   |
| `HashAlgorithm`  | The twelve fixed-length algorithms of `hashlib` (`md5` ... `blake2s`).                                |
| `WriterMode`     | The open modes of `SafeFileWriter`: `"w"`, `"wb"`, `"a"`, `"ab"`.                                    |

Use them in your own signatures so your functions accept exactly what this library does.

➡️ [README_FILE_ANNOTATIONS](https://github.com/simplibs/simplibs-file/blob/main/docs/README_FILE_ANNOTATIONS.md)

---

## 🪟 Platform Notes

The library is written for Windows and POSIX alike, and where they differ it says so:

* **Line endings:** the library writes `"\n"` everywhere unless you ask otherwise
  (`newline="\r\n"`, or `None` for the platform's own) — Python's text mode would silently
  write `\r\n` on Windows.
* **BOM:** reads tolerate it (`utf-8-sig`), writes do not add it. A BOM codec (`utf-8-sig`,
  `utf-16`) writes its BOM once, at the start of a new file — never again on an append.
* **Locks:** on Windows a short lock (an antivirus, the search indexer) is retried when a
  draft is swapped in or a file is moved; elsewhere a permission problem is real and raised at once.
* **Read-only files:** Windows cannot delete one — `delete_file(..., force=True)` clears the flag first.
* **Moves between disks** (`G:` → `C:`) fall back to an atomic copy followed by removing the source.
* **Durability:** `sync=True` flushes the file, and — where the OS allows it — the folder.
  Windows cannot flush a folder; there only the file is synced.
* **Case:** a case-only rename (`a.txt` → `A.txt`) is allowed on Windows.

---

## ⚠️ Exceptions

Functions raise structured [`simplibs.exception`](https://pypi.org/project/simplibs-exception/)
cards rather than bare `OSError`s and `UnicodeError`s:

| Exception            | Raised when                                                                                    |
|----------------------|------------------------------------------------------------------------------------------------|
| `ValidationError`    | An argument has the wrong type or value (a blank path, `encoding="rot13"`) — via `validate_call`. |
| `ParamError`         | An argument combination is unusable (source and destination are the same file, a malformed suffix). |
| `NotFoundError`      | A required file does not exist.                                                                |
| `StateError`         | The filesystem is in the wrong state (a directory where a file is needed, ...).                |
| `AlreadyExistsError` | The destination exists and `overwrite=False`.                                                  |
| `ConversionError`    | Bytes do not decode, a character cannot be encoded, JSON is malformed or cannot be serialized. |
| `AccessError`        | The operating system refused (permissions, a locked file, a full disk).                        |
| `OperationError`     | An operation ran out of options (no free numbered backup name left).                           |

Predicates (`is_text_file`, `rules/`) never raise for disk problems — they return `False`.

---

## 🔗 Related libraries

* **[`simplibs-path`](https://pypi.org/project/simplibs-path/)** — the paths themselves: normalize, check, ensure and scan. `simplibs-file` is built on it.
* **[`simplibs-rules`](https://pypi.org/project/simplibs-rules/)** — the `Rule` engine behind `simplibs.file.rules`.
* **[`simplibs-actions`](https://pypi.org/project/simplibs-actions/)** — the `Action` abstraction and containers behind `simplibs.file.actions`.
* **[`simplibs-validate`](https://pypi.org/project/simplibs-validate/)** — `@validate_call`, which validates every function argument here.
* **[`simplibs-exception`](https://pypi.org/project/simplibs-exception/)** — the structured exception cards.

---

## ☯️ About simplibs

All libraries in the **simplibs** (Simple Libraries) ecosystem share a common
engineering philosophy:

* **Dyslexia-friendly:**
We actively minimize cognitive load. Code is atomized into small, self-contained units,
files are named directly after the logical task they perform, and explanations describe
*why* something is designed, not just *what* it is.
* **Programmer's Zen:**
Nothing should be missing, and nothing should be superfluous. We value clean execution
paths and robust, understandable code architectures over rushed, messy feature sets.
* **Defensive Style:**
We actively anticipate edge cases and failure modes so that only safe operational paths
remain. Our code is built to degrade gracefully rather than crash unexpectedly.
* **Minimalism:**
Find the most direct path to the goal in as few operational steps as possible without
taking shortcuts on safety, readability, or completeness.
* **Code as Craft:**
Code should be pleasant to look at, readable at a glance, and evoke structural harmony.
We treat software engineering as a precision trade.

---

### 🤝 Contributing & Community

This is an **open-source project** built with love and care. We strongly believe in
community collaboration and welcome any feedback, bug reports, or feature ideas!

* **Want to contribute?** Feel free to open an Issue or submit a Pull Request.
* **Want to get in touch?** If you'd like to discuss the project further, collaborate,
  or just say hello, feel free to open a GitHub Issue or start a Discussion.

---

### 📝 License

This library is released under the **MIT License**. Build great things!

---
