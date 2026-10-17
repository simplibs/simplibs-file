# 📖 `logic/read` — Everything That Reads Content

The `read` package holds the functions that **read the content of a file**: raw bytes, the whole
text, a list of lines, a parsed JSON document — and a lazy line-by-line stream for files too big
to hold. They never change anything, and every failure — a missing file, bytes that do not decode,
broken JSON — is reported as a structured card instead of a bare `OSError` or `UnicodeDecodeError`.

```python
from simplibs.file import iter_lines, read_bytes, read_json, read_lines, read_text
```

Every function accepts its path as a [`PathLike`](../README_FILE_ANNOTATIONS.md) — a non-blank
`str` or a `Path` — and is wrapped in `@validate_call`, so a blank string or a wrong type is
rejected with a `ValidationError` before the body runs. All but `iter_lines` have an
[action](../README_FILE_ACTIONS.md#read) counterpart for pipelines (a generator is consumed once
and cannot be logged or re-run by the action machinery).

## How the readers are layered

```
read_bytes                       the core — the only function that reads the disk eagerly
   ├── read_text                 bytes → text, newlines normalized
   │      └── read_json          text → parsed value
   └── read_lines                bytes → text → list of lines

iter_lines                       a separate, lazy path: streams, never holds the file
```

Every text reader reads **bytes first** and decodes them **in memory**, so decoding exists once
and a `UnicodeDecodeError` — a `ValueError`, invisible to an `except OSError` — becomes a card
everywhere.

## Which one to use

| You need …                                              | Use                                |
|---------------------------------------------------------|------------------------------------|
| The exact bytes (hashing, binary parsing)               | `read_bytes`                       |
| The whole text, `"\n"` line endings                     | `read_text`                        |
| The lines — with or without their original endings      | `read_lines`                       |
| A config or manifest as data                            | `read_json`                        |
| A huge log, one line at a time, flat memory             | `iter_lines`                       |

## A note on the default encoding

The readers default to **`"utf-8-sig"`**: a BOM — which files saved by many Windows tools start
with — is removed if present, and files without one are read just as well. Plain `"utf-8"` would
keep it as a stray `"\ufeff"` and make `json.loads` fail. The write side stays BOM-free `"utf-8"`.
See [`EncodingName`](../README_FILE_ANNOTATIONS.md#encodingname) and
[`EncodingErrors`](../README_FILE_ANNOTATIONS.md#encodingerrors) for the options.

## A note on line endings

| Reader                    | What happens to `"\r\n"`, `"\r"`, `"\n"`                                       |
|---------------------------|--------------------------------------------------------------------------------|
| `read_text`               | All three become `"\n"` — the same result as `Path.read_text`.                 |
| `read_lines`              | Only these three end a line; with `keep_ends=True` each line keeps its **original** ending. |
| `iter_lines`              | The same rules as `read_lines`.                                                |
| `read_bytes`              | Nothing is translated.                                                         |

Form feeds and Unicode separators (`\x0c`, `\x85`, `\u2028`, ...) stay **inside** their line —
unlike `str.splitlines`.

## A note on errors

| Situation                                                       | Exception         |
|-----------------------------------------------------------------|-------------------|
| The file does not exist                                         | `NotFoundError`   |
| The path is not a regular file (a directory, a device)          | `StateError`      |
| The OS refuses the read (permissions, a locked file)            | `AccessError`     |
| The bytes are not valid text in the encoding; JSON is malformed | `ConversionError` |

A symlink is **followed** — the content behind it is what is read.

---

## 🧭 Table of Contents

* [`read_bytes`](#read_bytes)
* [`read_text`](#read_text)
* [`read_lines`](#read_lines)
* [`read_json`](#read_json)
* [`iter_lines`](#iter_lines)
* [The helpers behind them](#the-helpers-behind-them)

[⬅️ Back to main README](../../README.md#-logicread--everything-that-reads-content)

---

### `read_bytes`

Reads the full binary content of a file — the core every other reader is built on.

**Parameters:**

* `path` (*PathLike*): The file to read. A symlink is followed.

**Returns:**

* `bytes`: The file's raw bytes.

**Raises:**

* `NotFoundError`: The file does not exist.
* `StateError`: The path is not a regular file.
* `AccessError`: The OS refuses the read.

**Example usage:**

```python
read_bytes("logo.png")                      # -> b'\x89PNG\r\n\x1a\n...'
read_bytes("crlf.txt")                      # -> b'a\r\nb'   (nothing is translated)
read_bytes("empty.bin")                     # -> b''
read_bytes("some_folder")                   # raises StateError
```

**Under the hood:**

```python
@validate_call
def read_bytes(path: PathLike) -> bytes:
    source = resolve_source_file(path, "read")        # normalized, and a regular file

    try:
        return source.read_bytes()
    except OSError as caught_exc:
        raise_file_access_error(source, "read", caught_exc)
```

The type and existence checks come from `resolve_source_file`; the read itself is guarded, so a
locked file or a permission problem is an `AccessError` card, not a bare `PermissionError`.

[▲ Back to top](#-table-of-contents)

---

### `read_text`

Reads the full text of a file.

**Parameters:**

* `path` (*PathLike*): The file to read.
* `encoding` (*EncodingName*, keyword-only, default `"utf-8-sig"`): The text encoding. A BOM is
  removed if present; files without one are fine.
* `errors` (*EncodingErrors*, keyword-only, default `"strict"`): How to treat bytes the encoding
  cannot decode.

**Returns:**

* `str`: The decoded text, with line endings normalized to `"\n"`.

**Raises:**

* `NotFoundError`, `StateError`, `AccessError`: As for [`read_bytes`](#read_bytes).
* `ConversionError`: The bytes are not valid text in the encoding.

**Example usage:**

```python
read_text("notes.txt")                              # -> 'line one\nline two\n'
read_text("old_export.txt", encoding="cp1250")      # a legacy Czech export
read_text("damaged.txt", errors="replace")          # undecodable bytes become '\ufffd'
read_text("binary.bin")                             # raises ConversionError (offset of the bad byte in the card)
```

**Under the hood:**

```python
@validate_call
def read_text(path, *, encoding="utf-8-sig", errors="strict") -> str:
    source = normalize_path(path)                     # once — the decoder needs the path for its failure card

    text = decode_bytes(read_bytes(source), source, encoding=encoding, errors=errors)

    return text.replace("\r\n", "\n").replace("\r", "\n")      # "\r\n" first, or it would become two line ends
```

The result matches `Path.read_text`, so code that moves from `pathlib` keeps behaving. A caller
who needs the exact bytes of the line endings uses `read_lines(keep_ends=True)` or `read_bytes`.

[▲ Back to top](#-table-of-contents)

---

### `read_lines`

Reads a file as a list of lines.

**Parameters:**

* `path` (*PathLike*): The file to read.
* `encoding` (*EncodingName*, keyword-only, default `"utf-8-sig"`)
* `errors` (*EncodingErrors*, keyword-only, default `"strict"`)
* `keep_ends` (*bool*, keyword-only, default `False`): If `True`, every line keeps its
  **original** line ending.

**Returns:**

* `list[str]`: The lines, in order. An empty file gives `[]`; a final line without a terminator
  is returned as it is.

**Raises:**

* `NotFoundError`, `StateError`, `AccessError`: As for [`read_bytes`](#read_bytes).
* `ConversionError`: The bytes are not valid text in the encoding.

**Example usage:**

```python
read_lines("a.txt")                             # -> ['one', 'two', 'three']
read_lines("crlf.txt", keep_ends=True)          # -> ['one\r\n', 'two\r\n', 'three']
read_lines("mixed.txt", keep_ends=True)         # -> ['a\r\n', 'b\r', 'c\n', 'd']   (each ending preserved)
read_lines("empty.txt")                         # -> []

write_lines("copy.txt", read_lines("a.txt"))    # the round trip reproduces the file
```

**Under the hood:**

```python
@validate_call
def read_lines(path, *, encoding="utf-8-sig", errors="strict", keep_ends=False) -> list[str]:
    source = normalize_path(path)
    text = decode_bytes(read_bytes(source), source, encoding=encoding, errors=errors)

    lines = io.StringIO(text, newline="").readlines()       # newline="" leaves the endings untranslated

    return lines if keep_ends else [strip_line_ending(line) for line in lines]
```

`str.splitlines` also splits on `\x0b`, `\x0c`, `\x1c`–`\x1e`, `\x85`, `\u2028` and `\u2029` — a
source file containing a form feed would fall apart — and with `keepends=True` it returned
endings that were already translated. `StringIO(text, newline="")` splits only on real line
endings and keeps them exactly as they were. The whole file is loaded; for large files use
[`iter_lines`](#iter_lines).

[▲ Back to top](#-table-of-contents)

---

### `read_json`

Reads a file and parses its content as JSON.

**Parameters:**

* `path` (*PathLike*): The JSON file to read.
* `encoding` (*EncodingName*, keyword-only, default `"utf-8-sig"`): So a BOM written by a Windows
  tool does not break parsing.
* `errors` (*EncodingErrors*, keyword-only, default `"strict"`)

**Returns:**

* `Any`: The parsed value — a `dict`, `list`, `str`, `int`, `float`, `bool` or `None`.

**Raises:**

* `NotFoundError`, `StateError`, `AccessError`: As for [`read_bytes`](#read_bytes).
* `ConversionError`: The bytes are not valid text, **or** the text is not valid JSON — the card
  carries the line and the column.

**Example usage:**

```python
read_json("config.json")                        # -> {'debug': True, 'retries': 3}
read_json("list.json")                          # -> [1, 2, 3]
read_json("null.json")                          # -> None
read_json("broken.json")                        # raises ConversionError — "Expecting ',' delimiter (line 4, column 3)"
read_json("empty.json")                         # raises ConversionError
```

**Under the hood:**

```python
@validate_call
def read_json(path, *, encoding="utf-8-sig", errors="strict") -> Any:
    source = normalize_path(path)
    text = read_text(source, encoding=encoding, errors=errors)       # BOM tolerant

    try:
        return json.loads(text)
    except json.JSONDecodeError as caught_exc:
        raise_json_decode_error(source, caught_exc)                  # a card with line and column
```

`json.load` on a plain `utf-8` handle fails with "Unexpected UTF-8 BOM" on files saved by many
Windows tools — reading through `read_text` avoids that. The path must be a regular file (a
directory used to raise a raw `IsADirectoryError`). `NaN` is accepted, as in the standard library.
The whole document is held in memory; streaming large JSON is outside this library's scope.

[▲ Back to top](#-table-of-contents)

---

### `iter_lines`

Iterates over the lines of a file **lazily**, without loading it whole — the lazy counterpart
of [`read_lines`](#read_lines), with the same line rules and the same results.

**Parameters:**

* `path` (*PathLike*): The file to read.
* `encoding` (*EncodingName*, keyword-only, default `"utf-8-sig"`)
* `errors` (*EncodingErrors*, keyword-only, default `"strict"`)
* `keep_ends` (*bool*, keyword-only, default `False`): If `True`, every line keeps its
  **original** line ending.

**Returns:**

* `Iterator[str]`: A lazy iterator of lines. Close it (or exhaust it) to release the file.

**Raises:**

* **At the call** — `NotFoundError`, `StateError`: The path is not a regular file.
* **During iteration**, when that part of the file is reached — `ConversionError`, `AccessError`.

**Example usage:**

```python
for line in iter_lines("huge.log"):
    if "ERROR" in line:
        print(line)

lines = iter_lines("huge.log", keep_ends=True)
first = next(lines)                             # only the beginning of the file has been read
lines.close()                                   # release the file when you stop early

iter_lines("missing.log")                       # raises NotFoundError HERE, not at the first next()
```

**Under the hood:**

```python
@validate_call
def iter_lines(path, *, encoding="utf-8-sig", errors="strict", keep_ends=False) -> Iterator[str]:
    source = resolve_source_file(path, "read")      # fail early — reported here, not at the first next()

    return stream_lines(source, encoding=encoding, errors=errors, keep_ends=keep_ends)
```

`iter_lines` is an ordinary function that **returns** a generator, not a generator function. A
generator function runs none of its body — including the existence check — until the first
`next()`, so a typo in the path would surface far away from the mistake. Everything knowable up
front is raised at the call; what only the content can reveal (invalid bytes, an OS failure
mid-file) is raised during iteration. The text layer decodes in blocks of about 8 KB, so an
invalid byte can be reported slightly **before** its own line, and the card then omits the byte
offset (it would be relative to the block).

[▲ Back to top](#-table-of-contents)

---

### The helpers behind them

Three small internal helpers (not exported) carry the shared work of the text readers.

| Helper                                   | What it does                                                                         | Used by                                   |
|------------------------------------------|--------------------------------------------------------------------------------------|-------------------------------------------|
| `decode_bytes(data, source, *, encoding, errors)` | Bytes → text in memory; invalid bytes become a `ConversionError` card.      | `read_text`, `read_lines`                 |
| `stream_lines(source, *, encoding, errors, keep_ends)` | The generator behind `iter_lines`.                                    | `iter_lines`                              |
| `strip_line_ending(line)`                | Removes **exactly one** trailing `"\r\n"`, `"\n"` or `"\r"`.                         | `read_lines`, `stream_lines`              |

**`decode_bytes`** is the mirror of `encode_text` on the write side — decoding exists once:

```python
try:
    return data.decode(encoding, errors)
except UnicodeDecodeError as caught_exc:
    raise_decode_error(source, encoding, caught_exc)      # a card with the byte offset
```

**`stream_lines`** is a separate function because a function containing `yield` runs nothing
until it is iterated; the eager checks therefore live in `iter_lines` and only the streaming
lives here:

```python
try:
    with source.open("r", encoding=encoding, errors=errors, newline="") as handle:    # newline="" keeps the endings
        for line in handle:                                                           # one line at a time
            yield line if keep_ends else strip_line_ending(line)

except UnicodeDecodeError as caught_exc:                  # invalid bytes surface when that part is reached
    raise_decode_error(source, encoding, caught_exc, offset_known=False)

except OSError as caught_exc:                             # an OS failure in the middle of the file
    raise_file_access_error(source, "read", caught_exc)
```

**`strip_line_ending`** is not `rstrip`: `str.rstrip("\r\n")` would also eat characters that
belong to the line (`"a\r"` followed by an empty line is two lines in an untranslated read).

```python
if line.endswith("\r\n"):                 # the two-character ending first, or "\r\n" would lose only its "\n"
    return line[:-2]
if line.endswith(("\n", "\r")):
    return line[:-1]
return line                               # the last line of a file may have none
```

[▲ Back to top](#-table-of-contents)

---

[⬅️ Back to main README](../../README.md#-logicread--everything-that-reads-content)
