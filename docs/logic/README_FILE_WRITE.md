# ✍️ `logic/write` — Everything That Writes Content

The `write` package holds the functions that **write the content of a file**: raw bytes, text,
lines, joined fragments, a JSON document — and the appenders that add to an existing file. Every
one **changes the disk**, reports each failure as a structured card instead of a bare `OSError`
or `UnicodeEncodeError`, and returns the normalized `Path` of the target, so the result chains
straight into the next step.

```python
from simplibs.file import (
    append_bytes, append_text,
    write_aggregated, write_bytes, write_json, write_lines, write_text,
)
```

Every function accepts its path as a [`PathLike`](../README_FILE_ANNOTATIONS.md) — a non-blank
`str` or a `Path` — and is wrapped in `@validate_call`, so a blank string or a wrong type is
rejected with a `ValidationError` before the body runs. Each has [two action
counterparts](../README_FILE_ACTIONS.md#content-or-path--which-one-flows) for pipelines: one where the
**content** flows (`WriteText`) and one where the **path** flows (`WriteTextTo`).

## How the writers are layered

```
write_json ───────┐
write_lines ──────┼──► write_text ──► encode_text ──► write_bytes ──► SafeFileWriter (draft) / direct
write_aggregated ─┘

append_text ──────────► encode_text ──► append_bytes ──► SafeFileWriter (draft) / direct
```

* **Cores** — `write_bytes` and `append_bytes` are the only functions that reach the disk.
* **Text layer** — `write_text` and `append_text` encode in memory, then call a core.
* **Shapes of text** — `write_lines`, `write_aggregated` and `write_json` build the text, then
  call `write_text`; everything else (draft, encoding, newline) is inherited.

Because the draft logic exists **exactly once** — it used to be copied into five functions — a
fix or a guarantee made in a core holds for every writer.

## A note on encoding first

Every text writer **encodes in memory before the disk is touched**. Three old defects are gone
because of that order:

* `Path.write_text` truncated the file *before* encoding, so a `UnicodeEncodeError` left a
  truncated file behind;
* `UnicodeEncodeError` is a `ValueError`, so an `except OSError` never saw it;
* `json.dump` wrote in chunks, so a `TypeError` in the middle of a large structure left a
  half-written, invalid file.

An unencodable character is a `ConversionError` card, and the target is completely untouched.

## A note on drafts, `overwrite` and `sync`

| Option      | Meaning                                                                                                   |
|-------------|-----------------------------------------------------------------------------------------------------------|
| `use_draft` | `True`: the data goes into a private draft that **replaces** the target atomically ([`SafeFileWriter`](README_FILE_SAFE_WRITER.md)) — a failure never damages the old file. `False`: written in place — faster, but a failure can leave a partial file. |
| `overwrite` | `False`: an existing target raises `AlreadyExistsError` instead of being replaced.                         |
| `sync`      | Force the data to stable storage — survives a power loss, slower. Atomic alone means "safe against a crashing *process*". |

**Defaults differ on purpose.** The writers default to `use_draft=True` (safe by default); the
appenders to **`use_draft=False`**, because a safe append has to copy the whole existing file into
a draft first, and the cost would grow with every call (appending a log line to a 1 GB file would
copy 1 GB).

**`overwrite=False` and a race.** With a draft, the existence check is a **fail-fast message**, not
a guarantee: `os.replace` overwrites silently if the file appears in the last millisecond. The
in-place mode is exact — it opens the file in exclusive mode (`"xb"`). The same holds for
`overwrite=False` everywhere else in the library.

## A note on line endings and BOM

`newline` follows `open(newline=...)` on writes: every `"\n"` in the text becomes the chosen
ending (`"\n"` by default, `"\r\n"`, `"\r"`, or `None` for the platform's own). An existing
`"\r\n"` is therefore **not** recognized and would become `"\r\r\n"` — text that already has its
own endings is written as bytes. See [`NewlineMode`](../README_FILE_ANNOTATIONS.md#newlinemode).

A BOM codec (`utf-8-sig`, `utf-16`, `utf-32`) writes its BOM at the start of a **new** file —
which is what that encoding means. For an appender, a BOM in the middle of a file would be a
defect, so it is stripped when the target already has content.

## A note on errors

| Situation                                                        | Exception            |
|------------------------------------------------------------------|----------------------|
| A directory occupies the target                                  | `StateError`         |
| The target exists and `overwrite=False`                          | `AlreadyExistsError` |
| A character cannot be encoded; a value cannot be serialized to JSON | `ConversionError` |
| The OS refuses (permissions, a locked file, a full disk)         | `AccessError`        |

The target's folder is created when missing. A symlink at the path is followed — the **content**
behind it is written, and the link stays in place.

---

## 🧭 Table of Contents

* [`write_bytes`](#write_bytes)
* [`append_bytes`](#append_bytes)
* [`write_text`](#write_text)
* [`append_text`](#append_text)
* [`write_lines`](#write_lines)
* [`write_aggregated`](#write_aggregated)
* [`write_json`](#write_json)
* [The helpers behind them](#the-helpers-behind-them)

[⬅️ Back to main README](../../README.md#-logicwrite--everything-that-writes-content)

---

### `write_bytes`

Writes bytes to a file — the **first core** every other writer is built on.

**Parameters:**

* `path` (*PathLike*): The target file. Its folder is created if missing.
* `data` (*bytes*): The bytes to write. (`bytearray` is not accepted.)
* `overwrite` (*bool*, keyword-only, default `True`): If `False`, an existing file raises.
* `use_draft` (*bool*, keyword-only, default `True`): Atomic draft-and-swap, or an in-place write.
* `sync` (*bool*, keyword-only, default `False`): Force the data to stable storage.

**Returns:**

* `Path`: The normalized target.

**Raises:**

* `StateError`: A directory occupies the target.
* `AlreadyExistsError`: The target exists and `overwrite=False`.
* `AccessError`: The OS refuses the write.

**Example usage:**

```python
write_bytes("out/blob.bin", b"\x00\xff")                   # -> <cwd>/out/blob.bin  (out/ is created)
write_bytes("out/blob.bin", b"new", overwrite=False)       # raises AlreadyExistsError
write_bytes("out/big.bin", payload, use_draft=False)       # in place: faster, but a crash can leave a partial file
write_bytes("out/key.bin", secret, sync=True)              # survives a power loss
```

**Under the hood:**

```python
@validate_call
def write_bytes(path, data, *, overwrite=True, use_draft=True, sync=False) -> Path:
    target = prepare_write_target(path, "write", overwrite=overwrite)   # normalize, refuse a directory, make the folder

    # safe path — draft and swap
    if use_draft:
        try:
            with SafeFileWriter(target, mode="wb", sync=sync) as handle:
                handle.write(data)
        except SimpleException:                  # a card the writer already built passes through untouched
            raise
        except OSError as caught_exc:            # a raw OS failure while writing into the draft
            raise_file_access_error(target, "write", caught_exc)
        return target

    # direct path — exclusive mode closes the check-then-write gap when overwriting is forbidden
    try:
        with target.open("wb" if overwrite else "xb") as handle:
            handle.write(data)
            if sync:
                handle.flush()
                os.fsync(handle.fileno())
    except FileExistsError:
        raise_destination_exists_error(target, "write")
    except OSError as caught_exc:
        raise_file_access_error(target, "write", caught_exc)

    return target
```

The card pass-through (`except SimpleException: raise`) matters: cards raised by `SafeFileWriter`
may themselves be `OSError` subclasses (they keep the caught exception type), so they must not be
caught by `except OSError` and wrapped a second time. The direct mode is honest about its risk:
it truncates the target first, so a crash in the middle leaves a partial file — the documented
price of speed.

[▲ Back to top](#-table-of-contents)

---

### `append_bytes`

Appends bytes to a file, creating it if it does not exist — the **second core writer**.

**Parameters:**

* `path` (*PathLike*): The target file. Its folder is created if missing.
* `data` (*bytes*): The bytes to add after the existing content.
* `use_draft` (*bool*, keyword-only, default `False`): If `True`, the existing content is copied
  into a draft, the data appended there, and the draft swapped in — an interrupted append can
  never damage the old content, but the cost grows with the file size.
* `sync` (*bool*, keyword-only, default `False`): Force the data to stable storage.

There is **no** `overwrite`: appending to an existing file is the whole point.

**Returns:**

* `Path`: The normalized target.

**Raises:**

* `StateError`: A directory occupies the target.
* `AccessError`: The OS refuses the write.

**Example usage:**

```python
append_bytes("out/stream.bin", b"\x01\x02")                 # creates the file if it is missing
append_bytes("out/stream.bin", b"\x03")                     # file: b'\x01\x02\x03'
append_bytes("out/ledger.bin", b"entry", use_draft=True)    # all-or-nothing, at the cost of copying the file
append_bytes("out/empty.bin", b"")                          # creates an empty file
```

**Under the hood:**

```python
@validate_call
def append_bytes(path, data, *, use_draft=False, sync=False) -> Path:
    target = prepare_write_target(path, "append")        # appending never conflicts with an existing file

    # safe path — the draft starts as a copy of the existing content
    if use_draft:
        try:
            with SafeFileWriter(target, mode="ab", sync=sync) as handle:
                handle.write(data)
        except SimpleException:
            raise
        except OSError as caught_exc:
            raise_file_access_error(target, "append", caught_exc)
        return target

    # direct path — a plain append
    try:
        with target.open("ab") as handle:
            handle.write(data)
            if sync:
                handle.flush()
                os.fsync(handle.fileno())
    except OSError as caught_exc:
        raise_file_access_error(target, "append", caught_exc)

    return target
```

The in-place append is fast, and an interrupted one can at worst leave a partial **last** chunk —
the older content is never touched. Whoever needs the all-or-nothing guarantee asks for it with
`use_draft=True`.

[▲ Back to top](#-table-of-contents)

---

### `write_text`

Encodes text in memory and writes it to a file — the text face of [`write_bytes`](#write_bytes).

**Parameters:**

* `path` (*PathLike*): The target file. Its folder is created if missing.
* `text` (*str*): The text to write.
* `encoding` (*EncodingName*, keyword-only, default `"utf-8"`): No BOM.
* `errors` (*EncodingErrors*, keyword-only, default `"strict"`): How to treat characters the
  encoding cannot hold.
* `newline` (*NewlineMode*, keyword-only, default `"\n"`): The line ending written for every `"\n"`
  (`None` for the platform's own).
* `overwrite` (*bool*, keyword-only, default `True`), `use_draft` (*bool*, keyword-only,
  default `True`), `sync` (*bool*, keyword-only, default `False`): As for `write_bytes`.

**Returns:**

* `Path`: The normalized target.

**Raises:**

* `ConversionError`: A character cannot be encoded.
* `StateError`, `AlreadyExistsError`, `AccessError`: As for [`write_bytes`](#write_bytes).

**Example usage:**

```python
write_text("out/report.txt", "hello\n")                     # file: b'hello\n'
write_text("out/win.txt", "a\nb", newline="\r\n")           # file: b'a\r\nb'
write_text("out/czech.txt", "příliš", encoding="cp1250")
write_text("out/ascii.txt", "č", encoding="ascii", errors="replace")   # file: b'?'
write_text("out/ascii.txt", "č", encoding="ascii")          # raises ConversionError — the old file is intact
write_text("out/bom.txt", "a", encoding="utf-8-sig")        # file starts with the BOM
```

**Under the hood:**

```python
@validate_call
def write_text(path, text, *, encoding="utf-8", errors="strict", newline="\n",
               overwrite=True, use_draft=True, sync=False) -> Path:
    target = normalize_path(path)                       # once — the encoder needs the path for its failure card

    data = encode_text(text, target, encoding=encoding, errors=errors, newline=newline)   # may fail — disk untouched

    return write_bytes(target, data, overwrite=overwrite, use_draft=use_draft, sync=sync)
```

The defaults make the result **deterministic**: `utf-8` without a BOM and `"\n"` line endings.
Python's own text mode silently writes `\r\n` on Windows, so the same program would produce
different bytes on different machines; here anything else is an explicit choice.

[▲ Back to top](#-table-of-contents)

---

### `append_text`

Appends text to a file, creating it if it does not exist — the text face of
[`append_bytes`](#append_bytes).

**Parameters:**

* `path` (*PathLike*): The target file. Its folder is created if missing.
* `text` (*str*): The text to add after the existing content.
* `encoding` (*EncodingName*, keyword-only, default `"utf-8"`): Should match the file's existing encoding.
* `errors` (*EncodingErrors*, keyword-only, default `"strict"`)
* `newline` (*NewlineMode*, keyword-only, default `"\n"`)
* `use_draft` (*bool*, keyword-only, default `False`), `sync` (*bool*, keyword-only, default `False`):
  As for `append_bytes`.

**Returns:**

* `Path`: The normalized target.

**Raises:**

* `ConversionError`: A character cannot be encoded.
* `StateError`, `AccessError`: As for [`append_bytes`](#append_bytes).

**Example usage:**

```python
append_text("logs/run.log", "started\n")                    # creates logs/ and run.log
append_text("logs/run.log", "finished\n")                   # file: 'started\nfinished\n'
append_text("out/t.txt", "a", encoding="utf-8-sig")
append_text("out/t.txt", "b", encoding="utf-8-sig")         # exactly ONE BOM, at the start
```

**Under the hood:**

```python
@validate_call
def append_text(path, text, *, encoding="utf-8", errors="strict", newline="\n",
                use_draft=False, sync=False) -> Path:
    target = normalize_path(path)

    data = encode_text(text, target, encoding=encoding, errors=errors, newline=newline)   # the file is untouched if this fails

    data = drop_redundant_bom(data, target, encoding)       # a BOM belongs at the start of a file, never in the middle

    return append_bytes(target, data, use_draft=use_draft, sync=sync)
```

`utf-8-sig`, `utf-16` and `utf-32` emit a BOM on **every** `encode` call; without
`drop_redundant_bom`, two appends would leave a BOM in the middle of the file. **The caller owns
encoding consistency**: appending `cp1250` text to a `utf-8` file produces a mixed file, and the
library cannot tell what is already in it.

[▲ Back to top](#-table-of-contents)

---

### `write_lines`

Writes a collection of lines to a file, one per line — the counterpart of
[`read_lines`](README_FILE_READ.md#read_lines).

**Parameters:**

* `path` (*PathLike*): The target file. Its folder is created if missing.
* `lines` (*Collection[str]*): The lines, in order. A list, tuple or set — **not** a generator.
* `encoding` (*EncodingName*, keyword-only, default `"utf-8"`), `errors` (*EncodingErrors*,
  default `"strict"`), `newline` (*NewlineMode*, default `"\n"`): As for `write_text`.
* `trailing_newline` (*bool*, keyword-only, default `True`): If `True`, the last line is also
  terminated, as POSIX tools expect. An empty collection always gives an empty file.
* `overwrite` (*bool*, keyword-only, default `True`), `use_draft` (*bool*, default `True`),
  `sync` (*bool*, default `False`): As for `write_bytes`.

**Returns:**

* `Path`: The normalized target.

**Raises:**

* `ConversionError`, `StateError`, `AlreadyExistsError`, `AccessError`: As for `write_text`.

**Example usage:**

```python
write_lines("out/list.txt", ["a", "b"])                          # file: 'a\nb\n'
write_lines("out/list.txt", ["a", "b"], trailing_newline=False)  # file: 'a\nb'
write_lines("out/win.txt", ["a", "b"], newline="\r\n")           # file: 'a\r\nb\r\n'
write_lines("out/empty.txt", [])                                 # an empty file — never a lone newline

write_lines("out/copy.txt", read_lines("src.txt"))               # reproduces a file (default keep_ends=False)
```

**Under the hood:**

```python
text = "\n".join(lines)                    # joined with "\n" — write_text translates it to the chosen ending

if trailing_newline and lines:             # never turn an empty collection into a lone newline
    text += "\n"

return write_text(path, text, encoding=encoding, errors=errors, newline=newline,
                  overwrite=overwrite, use_draft=use_draft, sync=sync)
```

**Lines carry no line ending.** An item that already ends with `"\n"` is written as it is, so the
file gets an empty line after it; an item containing `"\n"` becomes more than one line. Items from
`read_lines(keep_ends=True)` belong in `write_text("".join(...))` instead. It takes a `Collection`,
not an `Iterable`: the lines are used twice (the join and the emptiness test), and `@validate_call`
must be able to inspect them without consuming a generator.

[▲ Back to top](#-table-of-contents)

---

### `write_aggregated`

Joins text fragments with a separator and writes them as **one file** — the step at the end of an
extraction pipeline, where several extracted texts become one document.

**Parameters:**

* `path` (*PathLike*): The target file. Its folder is created if missing.
* `parts` (*Collection[str]*): The fragments to join, in order.
* `separator` (*str*, keyword-only, default `"\n"`): Placed between consecutive fragments.
* `encoding`, `errors`, `newline`, `overwrite`, `use_draft`, `sync`: As for `write_text`.
* `trailing_newline` (*bool*, keyword-only, default `False`): If `True`, one `"\n"` is added after
  the last fragment.

**Returns:**

* `Path`: The normalized target.

**Raises:**

* `ConversionError`, `StateError`, `AlreadyExistsError`, `AccessError`: As for `write_text`.

**Example usage:**

```python
write_aggregated("out/all.txt", ["a", "b"])                           # file: 'a\nb'
write_aggregated("out/all.md", ["intro", "body"], separator="\n\n---\n\n")
write_aggregated("out/ids.txt", ["12", "34"], separator="")           # file: '1234'
write_aggregated("out/all.txt", ["a", "b"], trailing_newline=True)    # file: 'a\nb\n'

write_aggregated("build/combined.md", [read_text(p) for p in collect_files("notes")])
```

**Under the hood:**

```python
text = separator.join(parts)

if trailing_newline:
    text += "\n"

return write_text(path, text, encoding=encoding, errors=errors, newline=newline,
                  overwrite=overwrite, use_draft=use_draft, sync=sync)
```

Versus [`write_lines`](#write_lines): `write_lines` writes **one line per item** with line endings
supplied by the library; `write_aggregated` joins arbitrary chunks with an arbitrary separator
(`"\n\n"`, `"\n---\n"`, `""`). The exact join is the default — `trailing_newline` is opt-in,
unlike in `write_lines`.

[▲ Back to top](#-table-of-contents)

---

### `write_json`

Serializes a value to JSON and writes it to a file — the JSON face of [`write_text`](#write_text).

**Parameters:**

* `path` (*PathLike*): The target file. Its folder is created if missing.
* `data` (*Any*): The JSON-serializable value.
* `indent` (*int | str | None*, keyword-only, default `2`): Spaces, a string such as `"\t"`, or
  `None` for compact output.
* `ensure_ascii` (*bool*, keyword-only, default `False`): Non-ASCII characters are written as
  they are (`č`, not `\u010d`).
* `sort_keys` (*bool*, keyword-only, default `False`): Reproducible output, clean diffs.
* `allow_nan` (*bool*, keyword-only, default `False`): `NaN` / `Infinity` are refused — they are
  not valid JSON.
* `default` (*Callable | None*, keyword-only, default `None`): Converts objects JSON cannot
  serialize, like `json.dumps(default=...)`.
* `trailing_newline` (*bool*, keyword-only, default `True`): The file ends with a line ending.
* `encoding` (*EncodingName*, default `"utf-8"`), `newline` (*NewlineMode*, default `"\n"`),
  `overwrite`, `use_draft`, `sync`: As for `write_text`. There is **no** `errors` parameter.

**Returns:**

* `Path`: The normalized target.

**Raises:**

* `ConversionError`: The value cannot be serialized (an unserializable type, a circular
  reference, `NaN`, mixed-type keys with `sort_keys=True`) or encoded.
* `StateError`, `AlreadyExistsError`, `AccessError`: As for `write_bytes`.

**Example usage:**

```python
write_json("out/index.json", {"b": 1, "a": 2}, sort_keys=True)
# out/index.json:  {\n  "a": 2,\n  "b": 1\n}\n

write_json("out/compact.json", {"a": 1}, indent=None)             # {"a": 1}\n
write_json("out/czech.json", {"jméno": "Čeněk"})                  # readable, not \u010c...
write_json("out/paths.json", {"root": Path("src")}, default=str)  # custom types through `default`
write_json("out/bad.json", {"x": object()})                       # raises ConversionError — the old file is intact
write_json("out/null.json", None)                                 # file: 'null\n'
```

**Under the hood:**

```python
@validate_call
def write_json(path, data, *, indent=2, ensure_ascii=False, sort_keys=False, allow_nan=False,
               default=None, trailing_newline=True, encoding="utf-8", newline="\n",
               overwrite=True, use_draft=True, sync=False) -> Path:
    target = normalize_path(path)

    try:                                               # serialize in memory; the file is untouched if this fails
        text = json.dumps(data, indent=indent, ensure_ascii=ensure_ascii, sort_keys=sort_keys,
                          allow_nan=allow_nan, default=default)
    except (TypeError, ValueError) as caught_exc:
        raise_json_encode_error(target, caught_exc)

    if trailing_newline:                               # a text file ends with a line ending
        text += "\n"

    return write_text(target, text, encoding=encoding, newline=newline,
                      overwrite=overwrite, use_draft=use_draft, sync=sync)
```

Three defaults differ from `json.dump` on purpose: `ensure_ascii=False` keeps Czech and other text
readable; `allow_nan=False` fails loudly at write time rather than produce a file other tools
cannot read; `trailing_newline=True` makes the file end like any text file. `errors` is not
offered: JSON is almost always UTF-8, where nothing is unencodable — for another encoding, an
unencodable character is a real error and a `ConversionError` card is the right answer.

[▲ Back to top](#-table-of-contents)

---

### The helpers behind them

Three small internal helpers (not exported) carry the shared work of the writers.

| Helper                                          | What it does                                                                                 | Used by                                       |
|-------------------------------------------------|----------------------------------------------------------------------------------------------|-----------------------------------------------|
| `encode_text(text, target, *, encoding, errors, newline)` | Text → bytes in memory: line endings first, then the encoding.                      | `write_text`, `append_text`                   |
| `drop_redundant_bom(data, target, encoding)`    | Strips the BOM from freshly encoded text that is about to be **appended** to existing content. | `append_text`                               |
| `prepare_write_target(path, operation, *, overwrite)` | Normalize, refuse a directory, honour `overwrite`, create the folder.                  | `write_bytes`, `append_bytes`                 |

**`encode_text`** is the first half of every text write, and the mirror of `decode_bytes` on the
read side — it is why a bad character leaves the target completely untouched:

```python
line_ending = os.linesep if newline is None else newline        # None means the platform's own

if line_ending != "\n":                                         # the same rule as `open(newline=...)`
    text = text.replace("\n", line_ending)

try:
    return text.encode(encoding, errors)                        # in memory — the disk has not been touched
except UnicodeEncodeError as caught_exc:
    raise_encode_error(target, encoding, caught_exc)            # names the character and its position
```

**`drop_redundant_bom`** finds the BOM without a hard-coded list of codec names — `"".encode(encoding)`
is exactly what a codec writes in front of any chunk (`b""` for ordinary encodings, the BOM for the
BOM codecs):

```python
preamble = "".encode(encoding)
if not preamble or not data.startswith(preamble):
    return data

try:
    has_content = target.is_file() and target.stat().st_size > 0
except OSError:
    return data

return data[len(preamble):] if has_content else data        # an empty or new file keeps its BOM
```

It is only needed on this bytes-based path: `SafeFileWriter`'s text handle is a real
`TextIOWrapper`, which knows it appends to a non-empty file and writes no second BOM.

**`prepare_write_target`** is the shared start of both core writers:

```python
target = normalize_path(path)                       # a symlink is followed, the CONTENT behind it is written

is_dir = target.is_dir()
exists = target.exists()                            # (a refusal of the OS is an AccessError card)

if is_dir:                                          # a directory can never become a file
    raise_destination_is_dir_error(target, operation)

if exists and not overwrite:                        # an existing file is only replaced when the caller allows it
    raise_destination_exists_error(target, operation)

ensure_parent_dir(target)                           # guarantee the folder the file will live in
return target
```

`SafeFileWriter` repeats the folder and directory guard because it is also a public class used on
its own; both are idempotent and cost one `stat`.

[▲ Back to top](#-table-of-contents)

---

[⬅️ Back to main README](../../README.md#-logicwrite--everything-that-writes-content)
