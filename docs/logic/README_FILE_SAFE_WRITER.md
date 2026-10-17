# 🛡️ `logic/safe_writer` — Crash-Safe Writing

The `safe_writer` package holds the **one place in the library that knows how to replace a file
safely**: the `SafeFileWriter` context manager, and `IGNORE_DRAFTS`, the scanner pattern for its
leftovers. Every writer of the library ([`write_bytes`](README_FILE_WRITE.md#write_bytes),
[`append_bytes`](README_FILE_WRITE.md#append_bytes), and through them all the text and JSON
writers) goes through it unless the caller opts out with `use_draft=False`.

```python
from simplibs.file import IGNORE_DRAFTS, SafeFileWriter

with SafeFileWriter("out/data.json") as handle:
    handle.write('{"a": 1}')
# out/data.json now holds the complete new content — or, if anything above had failed,
# exactly what it held before
```

Unlike the functions of the other packages, this is a **class**, so the cards below describe its
**methods** rather than functions.

## The idea: draft and swap

Writes do not go into the target. They go into a **private draft** next to it, and the draft
replaces the target in **one atomic step** — only when the `with` block ends without an exception.

```
1. __enter__   create a unique draft next to the target and open it
2. the block   you write into the draft; the target is not touched
3. __exit__    no exception  → close the draft, swap it in (os.replace)
               an exception  → delete the draft; the target stays exactly as it was
```

## What it guarantees

* The target is replaced in **one `os.replace`** — a reader sees the old file or the new one,
  never half of each.
* An exception inside the `with` block, a failed close (a full disk shows up there) and a failed
  swap all leave the **original untouched** and remove the draft.
* **Safe against a crashing process.** Against a **power loss** only with `sync=True`: the draft is
  flushed before the swap and, where the OS allows it, the folder afterwards. (Windows cannot
  `fsync` a folder; there only the file is synced.)
* **Permissions survive.** `os.replace` puts a *new* inode in place, so without care a `0o600`
  secrets file would silently become `0o644`. The mode of the file being replaced is copied onto
  the draft first; a new file honours the umask, exactly like a plain `open()`.
* **Two writers of one target never interleave.** Every draft has a unique name, so two writers get
  two drafts and the last commit wins.

## Modes

The four modes are the [`WriterMode`](../README_FILE_ANNOTATIONS.md#writermode) literal:

| Mode   | Meaning                                                                                           |
|--------|---------------------------------------------------------------------------------------------------|
| `"w"`  | Overwrite, text.                                                                                  |
| `"wb"` | Overwrite, binary.                                                                                |
| `"a"`  | Append, text — the draft starts as a **copy** of the existing content.                            |
| `"ab"` | Append, binary — the same.                                                                        |

An append has to copy the whole existing file into the draft first, so its cost **grows with the
file** — which is why [`append_*`](README_FILE_WRITE.md#a-note-on-drafts-overwrite-and-sync)
default to a plain in-place append and offer `use_draft=True` as the opt-in.

## A note on symlinks and BOM

* The path is **normalized** (symlinks resolved): writing through a link replaces the file the
  link points to and leaves the link in place.
* In text append mode Python's own `TextIOWrapper` knows the draft already has content and does
  **not** write a second BOM for `utf-8-sig` / `utf-16`.

## A note on being single-use

`__exit__` resets the writer's state. Entering a used instance again simply creates a new draft,
but the instance is meant for **one** `with` statement.

---

## 🧭 Table of Contents

**`SafeFileWriter`**

* [`SafeFileWriter(...)` — the constructor](#safefilewriter--the-constructor)
* [`__enter__`](#__enter__)
* [`__exit__`](#__exit__)

**The rest of the package**

* [`IGNORE_DRAFTS`](#ignore_drafts)
* [The draft helpers](#the-draft-helpers)

[⬅️ Back to main README](../../README.md#-logicsafe_writer--crash-safe-writing)

---

### `SafeFileWriter` — the constructor

Prepares a writer for a target path and mode. **Nothing touches the disk yet.**

**Parameters:**

* `target_path` (*PathLike*): The file this writer will ultimately produce.
* `mode` (*WriterMode*, keyword-only, default `"w"`): `"w"` / `"wb"` to overwrite, `"a"` / `"ab"` to append.
* `encoding` (*EncodingName*, keyword-only, default `"utf-8"`): Text encoding of the handle.
  Ignored in binary modes.
* `errors` (*EncodingErrors*, keyword-only, default `"strict"`): Handling of unencodable
  characters. Ignored in binary modes.
* `newline` (*NewlineMode*, keyword-only, default `"\n"`): The line ending written for every
  `"\n"` (`None` for the platform's own). Ignored in binary modes.
* `sync` (*bool*, keyword-only, default `False`): Force the finished file to stable storage before
  the swap completes (slower, survives a power loss).

**Raises:**

* `ValidationError`: A wrong type or value of an argument — `mode="x"`, `encoding="rot13"`, a blank path.

**Example usage:**

```python
SafeFileWriter("out/report.txt")                                    # text, overwrite, UTF-8, "\n"
SafeFileWriter("out/data.bin", mode="wb")                           # binary
SafeFileWriter("logs/run.log", mode="a")                            # append (copy-append-swap)
SafeFileWriter("out/win.txt", newline="\r\n", encoding="cp1250")    # explicit choices
SafeFileWriter("out/key.bin", mode="wb", sync=True)                 # durable across a power loss
SafeFileWriter("out/data.bin", mode="x")                            # raises ValidationError — "x" and "r+" are not offered
```

**Under the hood:**

```python
class SafeFileWriter:
    __slots__ = ("_target_path", "_mode", "_encoding", "_errors", "_newline", "_sync",
                 "_draft_path", "_handle")

    @validate_call
    def __init__(self, target_path, *, mode="w", encoding="utf-8", errors="strict",
                 newline="\n", sync=False) -> None:
        # the settings are stored; the path is normalized once, here
        self._target_path = normalize_path(target_path)
        self._mode = mode
        self._encoding = encoding
        self._errors = errors
        self._newline = newline
        self._sync = sync

        # no draft and no handle yet
        self._draft_path: Path | None = None
        self._handle: IO[Any] | None = None
```

The old `mode: str` accepted `"x"` and `"r+"` and silently behaved as `"w"`; a literal of exactly
the four modes that make sense turns that into an immediate, readable error. Exclusive creation
and in-place update contradict the draft-and-swap idea — the target is only ever replaced **as a
whole**.

[▲ Back to top](#-table-of-contents)

---

### `__enter__`

Creates the draft, opens it for writing and **hands the open handle to the caller**
(`with SafeFileWriter(...) as handle`).

**Returns:**

* `IO[Any]`: The open handle of the draft — a text handle for `"w"` / `"a"`, a binary one for
  `"wb"` / `"ab"`.

**Raises:**

* `StateError`: A directory occupies the target (it can never be replaced by a file).
* `AccessError`: The draft cannot be created (`SAFE_WRITER_DRAFT_CREATE_FAILED` — the folder is not
  writable, the disk is full) or cannot be opened (`SAFE_WRITER_DRAFT_OPEN_FAILED`). In both cases
  the target has not been touched, and a draft that was already created is removed first.

**Example usage:**

```python
with SafeFileWriter("out/report.txt") as handle:        # the draft exists from here on
    handle.write("first line\n")
    handle.write("second line\n")

with SafeFileWriter("out/data.bin", mode="wb") as handle:
    handle.write(b"\x00\xff")

with SafeFileWriter("logs/run.log", mode="a") as handle:    # the draft already holds the old content
    handle.write("another line\n")                          # ... so this continues after it
```

**Under the hood:**

```python
def __enter__(self) -> IO[Any]:
    # 1. guarantee the target's folder
    ensure_parent_dir(self._target_path)

    # 2. a directory at the target can never be replaced by a file
    if self._target_path.is_dir():
        raise_destination_is_dir_error(self._target_path, self._operation)

    # 3. create the draft — pre-filled with the existing content for append modes
    try:
        self._draft_path = create_draft(self._target_path, append=self._is_append)
    except OSError as caught_exc:
        raise_safe_writer_draft_create_error(self._target_path, caught_exc)

    # 4. open it; a failure removes the draft that was just created
    try:
        self._handle = self._open_draft()
    except OSError as caught_exc:
        delete_draft(self._draft_path)
        self._draft_path = None
        raise_safe_writer_draft_open_error(self._target_path, caught_exc)

    # 5. hand the open handle to the caller
    return self._handle
```

The draft is opened by a small internal method. For an append it is opened in plain `"a"`, because
the draft already holds the old content; binary modes get no encoding and no newline handling; text
modes get the requested `encoding`, `errors` and `newline`:

```python
def _open_draft(self):
    open_mode = "a" if self._is_append else "w"            # append drafts already hold the old content

    if "b" in self._mode:
        return self._draft_path.open(open_mode + "b")      # binary — no encoding, no newline handling

    return self._draft_path.open(open_mode, encoding=self._encoding,
                                 errors=self._errors, newline=self._newline)
```

An earlier version leaked the draft when opening it failed; now it is deleted **before** the card
is raised.

[▲ Back to top](#-table-of-contents)

---

### `__exit__`

**Commits the draft on success, discards it on any failure.** This is where the guarantee is kept.

**Parameters:**

* `exc_type`, `exc_value`, `traceback`: The exception that ended the `with` block, if any
  (the standard context-manager arguments).

**Returns:**

* `bool`: Always `False` — an exception is **never suppressed**.

**Raises:**

* `AccessError`: The draft could not be closed completely (`FILE_WRITE_FAILED` / `FILE_APPEND_FAILED` —
  a full disk shows up here), or the swap failed (`SAFE_WRITER_COMMIT_FAILED`). The original file is
  unchanged and the draft is discarded in both cases.

**Example usage:**

```python
try:
    with SafeFileWriter("config.json") as handle:
        handle.write("{")                               # half a document ...
        raise RuntimeError("something went wrong")      # ... and a failure
except RuntimeError:
    pass
# config.json is exactly as it was before; no .draft is left next to it

with SafeFileWriter("config.json") as handle:           # no exception → the swap happens at the end of the block
    handle.write('{"ok": true}')
```

**Under the hood:**

```python
def __exit__(self, exc_type, exc_value, traceback) -> bool:
    # 1. take the state and reset it — a writer instance is single-use
    handle, draft_path = self._handle, self._draft_path
    self._handle, self._draft_path = None, None

    # 2. close the handle first; remember a failure instead of raising it
    close_error = None
    if handle is not None:
        try:
            handle.close()
        except OSError as caught_exc:
            close_error = caught_exc

    # 3. an exception from the block wins — discard the draft, keep the original, let it propagate untouched
    if exc_type is not None:
        delete_draft(draft_path)
        return False

    # 4. the data never fully reached the draft — discard it and say so
    if close_error is not None:
        delete_draft(draft_path)
        raise_file_access_error(self._target_path, self._operation, close_error)

    # 5. success — swap the draft in; a failed swap leaves the original untouched
    try:
        commit_draft(draft_path, self._target_path, sync=self._sync)
    except OSError as caught_exc:
        delete_draft(draft_path)
        raise_safe_writer_commit_error(self._target_path, caught_exc)

    # 6. never suppress an exception
    return False
```

The **order** is the point. The earlier writer closed the handle first, and if the close failed (a
full disk) the exception flew out *before* the draft was deleted — leaking the draft and hiding
the real error. Now a close failure is **remembered** and reported only when the block itself
succeeded; an exception from the block always wins. Two internal properties name the operation in
the failure cards: `_is_append` is `"a" in mode`, and `_operation` is `"append"` or `"write"`.

[▲ Back to top](#-table-of-contents)

---

### `IGNORE_DRAFTS`

The names of the temporary drafts `SafeFileWriter` leaves next to a target — a glob pattern for
the scanners' `ignore_names`. **Opt-in.**

**Definition:**

```python
IGNORE_DRAFTS: Final[frozenset[str]] = frozenset({
    ".*.????????.draft",
})
```

**Example usage:**

```python
from simplibs.path import DEFAULT_IGNORE_NAMES, collect_files
from simplibs.file import IGNORE_DRAFTS

collect_files("project", ignore_names=DEFAULT_IGNORE_NAMES | IGNORE_DRAFTS)   # leftovers are not collected
```

| Name                       | Matches? | Why                                                         |
|----------------------------|:--------:|-------------------------------------------------------------|
| `.report.txt.a1b2c3d4.draft` | ✅      | a hidden name with exactly an 8-character middle part       |
| `essay.draft`              | ❌       | a user's own file — a blanket `*.draft` would have hidden it |
| `.notes.draft`             | ❌       | no 8-character middle part                                  |
| `.a.b.draft`               | ❌       | the same                                                    |

**Why it exists.** A draft exists for the milliseconds of a write — or **forever**, after a crash
or a locked file. A scan that runs in the same folder must not pick it up as a real file. The
pattern is **narrow on purpose**: drafts are named `.<name>.<8 hex>.draft`, so only a hidden name
with exactly that shape is ignored.

**Why it is not in `DEFAULT_IGNORE_NAMES`.** That default lives in `simplibs-path`, which knows
nothing about this library. Extend it with a union, as above.

[▲ Back to top](#-table-of-contents)

---

### The draft helpers

The three steps of a draft live in `logic/_common/helpers` (not exported), because a **copy**
shares them with the writer — `copy_atomically` uses the same three. Together they are
`SafeFileWriter`'s engine.

| Helper                                   | What it does                                                                               |
|------------------------------------------|--------------------------------------------------------------------------------------------|
| `create_draft(target_path, *, append)`   | Creates the unique, empty draft next to the target; for an append, pre-filled with the existing content. |
| `commit_draft(draft_path, target_path, *, keep_mode=True, sync=False)` | Atomically replaces the target with the finished draft. |
| `delete_draft(draft_path)`               | Discards a draft — quietly, whatever happens.                                              |

**`create_draft`** reserves a unique name by creating the file **exclusively**, in the same folder
as the target (`os.replace` is only atomic within one filesystem):

```python
flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0)
base_name = target_path.name[:100]                                  # a long name is cut — the 255 limit is never exceeded

for _ in range(100):
    candidate = target_path.with_name(f".{base_name}.{secrets.token_hex(4)}.draft")
    try:
        descriptor = os.open(candidate, flags, 0o666)               # 0o666: the umask decides, like a plain open()
    except FileExistsError:
        continue
    os.close(descriptor)
    draft_path = candidate
    break

if append and target_path.is_file():                                # append: start from a copy of the old content
    shutil.copyfile(target_path, draft_path)
```

A fixed `name.draft` would have meant two writers sharing and interleaving in one draft, and a
leftover from a crash being silently reused by the next run. `tempfile.mkstemp` was not used because
it always creates the file with mode `0o600`, which would make a **new** target more private than a
plain `open()` would. A failure while copying removes the draft again — the caller never cleans up
after a failed `create_draft`.

**`commit_draft`** is the atomic swap:

```python
if keep_mode and target_path.is_file():                 # a new inode would otherwise reset the permissions
    shutil.copymode(target_path, draft_path)

if sync:                                                # make the draft's data reach the disk first
    with draft_path.open("r+b") as handle:
        os.fsync(handle.fileno())

replace_with_retry(draft_path, target_path, attempts=attempts, delay=delay)   # short Windows locks are retried

if sync and os.name != "nt":                            # persist the rename itself (not possible on Windows)
    descriptor = os.open(target_path.parent, os.O_RDONLY)
    os.fsync(descriptor)
```

`keep_mode=False` is for a **copy**, which must end up with the permissions of its *source*, not
those of the file it replaces. The helper raises and does not wrap: the caller (`SafeFileWriter`,
`copy_atomically`) knows the context and builds the card.

**`delete_draft`** is cleanup that never throws — called on every failure path, it must not replace
the **original** error (a full disk, a permission problem) with a less useful one:

```python
if draft_path is None:                  # nothing was ever created
    return
try:
    draft_path.unlink(missing_ok=True)
except OSError:                         # never hide the error that led here
    pass
```

In the rare case a draft cannot be removed (locked by an antivirus), an orphan `.name.xxxxxxxx.draft`
stays next to the target — which is exactly what [`IGNORE_DRAFTS`](#ignore_drafts) keeps scanners
from collecting.

[▲ Back to top](#-table-of-contents)

---

[⬅️ Back to main README](../../README.md#-logicsafe_writer--crash-safe-writing)
