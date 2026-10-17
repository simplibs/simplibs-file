# 🗂️ `logic/operations` — Work with the File Itself

The `operations` package holds the functions that treat a file **as a whole**: copy it, move
or rename it, delete it, back it up. Each one **changes the disk**, reports every failure as a
structured card instead of a bare `OSError`, and returns the normalized `Path` of what it
produced — the copy, the new location, the deleted entry, the backup — so the result chains
straight into the next step.

```python
from simplibs.file import backup_file, copy_file, delete_file, move_file, rename_file
```

Every function accepts its paths as a [`PathLike`](../README_FILE_ANNOTATIONS.md) — a
non-blank `str` or a `Path` — and is wrapped in `@validate_call`, so a blank string or a wrong
type is rejected with a `ValidationError` before the body runs. Each has an
[action](../README_FILE_ACTIONS.md#operations) counterpart for pipelines.

## A note on atomicity

Copies — and with them backups and the cross-device fallback of a move — never write into
the destination directly. The data goes into a **private draft** next to it and is swapped in
at the end, with the same mechanism the writers use ([`SafeFileWriter`](README_FILE_SAFE_WRITER.md)).
An interruption therefore leaves either the **complete** copy or the destination exactly as it
was — never a truncated file that looks real. For a backup that is the difference between a
backup and a trap.

## A note on "entry" and "content" semantics

A path can lead to a symlink, and an operation has to decide whether "this path" means the
**link** or the file **behind** it. The functions decide by what they do:

| Function      | Normalizes with                                              | A symlink at the path means …                             |
|---------------|--------------------------------------------------------------|-----------------------------------------------------------|
| `copy_file`   | `normalize_path` (symlinks resolved)                         | the **content** — it is copied to where the destination path leads |
| `backup_file` | the source is resolved the same way                          | the **content** — the backup lives next to the *real* file |
| `move_file`   | `normalize_entry_path` (only the folder resolved)            | the **entry** — a link is moved as a link                 |
| `delete_file` | `normalize_entry_path`                                       | the **entry** — the link is deleted, its target survives  |

[`normalize_entry_path`](https://pypi.org/project/simplibs-path/) resolves the containing
directory but keeps the final name as written; that is what lets `delete_file("link")` remove
the link instead of the file it points to.

## A note on overwriting and races

`overwrite=False` (the default of `copy_file` and `move_file`) is a **fail-fast check with a
good message**, not a reservation: between the check and the swap another process can create
the destination, and the swap then replaces it. The same holds for the name a backup chooses.
A real operation still handles its own errors; these checks only make the common mistake
cheap to see.

## A note on errors

| Situation                                                                   | Exception            |
|-----------------------------------------------------------------------------|----------------------|
| The source (or the file to delete) does not exist                           | `NotFoundError`      |
| The source is a directory or a special entry; a directory occupies the destination | `StateError`   |
| Source and destination are the same file; a malformed backup `suffix`       | `ParamError`         |
| The destination exists and `overwrite=False`                                | `AlreadyExistsError` |
| No free numbered backup name can be found                                   | `OperationError`     |
| The OS refuses (permissions, a locked file, a full disk, a bad name)        | `AccessError`        |

A card about a copy, a move or a backup shows **both** paths (`file 'a.txt' -> 'b/a.txt'`)
together with what the OS reported.

---

## 🧭 Table of Contents

* [`copy_file`](#copy_file)
* [`move_file`](#move_file)
* [`rename_file`](#rename_file)
* [`delete_file`](#delete_file)
* [`backup_file`](#backup_file)
* [The helpers behind them](#the-helpers-behind-them)

[⬅️ Back to main README](../../README.md#-logicoperations--work-with-the-file-itself)

---

### `copy_file`

Copies a file to a new path, keeping its permissions and times. The copy is **atomic**.

**Parameters:**

* `source` (*PathLike*): The file to copy. A symlink is followed.
* `destination` (*PathLike*): The target **file** path — never a folder to copy into. Its
  folder is created if missing.
* `overwrite` (*bool*, keyword-only, default `False`): If `False`, an existing destination raises.
* `sync` (*bool*, keyword-only, default `False`): Force the copy to stable storage before it
  becomes visible (survives a power loss; slower).

**Returns:**

* `Path`: The normalized destination.

**Raises:**

* `NotFoundError` / `StateError`: The source is missing or is not a regular file.
* `ParamError`: Source and destination are the same file.
* `StateError`: A directory occupies the destination.
* `AlreadyExistsError`: The destination exists and `overwrite=False`.
* `AccessError`: The OS refuses the copy.

**Example usage:**

```python
copy_file("report.txt", "backup/report.txt")        # -> <cwd>/backup/report.txt  (backup/ is created)
copy_file("report.txt", "backup/report.txt")        # raises AlreadyExistsError — it is already there
copy_file("report.txt", "backup/report.txt", overwrite=True)

copy_file("report.txt", "backup")                   # backup/ is a directory -> StateError, NOT "copy into it"
copy_file("report.txt", "report.txt")               # raises ParamError — the same file
```

**Under the hood:**

```python
@validate_call
def copy_file(source, destination, *, overwrite=False, sync=False) -> Path:
    source_path = resolve_source_file(source, "copy")            # normalized, and a regular file
    destination_path = normalize_path(destination)

    prepare_destination(source_path, destination_path, "copy", overwrite=overwrite)   # same file? a directory? already there?
    ensure_parent_dir(destination_path)

    try:
        copy_atomically(source_path, destination_path, sync=sync)   # through a draft
    except OSError as caught_exc:
        raise_file_transfer_error(source_path, destination_path, "copy", caught_exc)   # a card showing both paths

    return destination_path
```

`shutil.copy2(src, folder)` copies *into* a folder, so a destination that is a directory used
to produce a file at a different path than the one returned. Here the destination is always
the file's own path, and an existing directory there is a clear `StateError`. Copying a file
onto itself is refused instead of truncating it. Source and destination are normalized with
symlinks resolved: the **content** is copied to where the destination path leads.

[▲ Back to top](#-table-of-contents)

---

### `move_file`

Moves or renames a file — across folders **and across devices** — working on the directory
**entry**: a symlink is moved as a link, not as the file it points to.

**Parameters:**

* `source` (*PathLike*): The file (or symlink) to move.
* `destination` (*PathLike*): The new **file** path. Its folder is created if missing.
* `overwrite` (*bool*, keyword-only, default `False`): If `False`, an existing destination raises.

There is **no** `sync` parameter: a same-device rename has no data to flush, and a power-loss
guarantee for the rename itself would need a folder `fsync` that Windows does not offer. The
parameter would promise more than it can keep.

**Returns:**

* `Path`: The normalized destination.

**Raises:**

* `NotFoundError`: The source does not exist.
* `StateError`: The source is a directory (or a special entry), or a directory occupies the destination.
* `ParamError`: Source and destination are the same file.
* `AlreadyExistsError`: The destination exists and `overwrite=False`.
* `AccessError`: The OS refuses the move.

**Example usage:**

```python
move_file("report.txt", "archive/2026/report.txt")      # archive/2026/ is created
move_file("a.txt", "A.txt", overwrite=True)             # a case-only rename works, also on Windows

move_file("link.txt", "moved_link.txt")                 # the LINK is moved; its target stays where it was
move_file("report.txt", "G:/backup/report.txt")         # another device — copy, then remove the source
```

**Under the hood:**

```python
@validate_call
def move_file(source, destination, *, overwrite=False) -> Path:
    source_path = normalize_entry_path(source)               # a symlink in the final position stays a symlink
    destination_path = normalize_entry_path(destination)

    # the source must be an existing file ENTRY (a dangling symlink counts)
    exists = os.path.lexists(source_path)
    is_file_entry = exists and (source_path.is_symlink() or source_path.is_file())
    if not exists:
        raise_file_not_found_error(source_path, "move")
    if not is_file_entry:
        raise_not_a_file_error(source_path, "move")

    prepare_destination(source_path, destination_path, "move", overwrite=overwrite)
    ensure_parent_dir(destination_path)

    try:
        replace_with_retry(source_path, destination_path)            # one atomic rename
    except OSError as caught_exc:
        if not is_cross_device_error(caught_exc):                    # anything but "different device" is real
            raise_file_transfer_error(source_path, destination_path, "move", caught_exc)
        try:
            move_across_devices(source_path, destination_path)       # copy completely, then remove the source
        except OSError as fallback_exc:
            raise_file_transfer_error(source_path, destination_path, "move", fallback_exc)

    return destination_path
```

`os.replace` between `G:` and `C:` fails (`WinError 17`, `EXDEV`) — not a failure of the
move, only a signal to **copy and then delete**. The order is the safety: if the copy fails the
source is untouched; if only the final delete fails, both files exist and no data is lost.
A symlink cannot be moved to another device this way (recreating a link elsewhere is a
different operation); that is refused with a clear message instead of silently turning the
link into a file. Windows file locks are retried (`replace_with_retry`), as when a writer
swaps its draft in. A case-only rename (`a.txt` → `A.txt`) is the same file to Windows and still
a legitimate rename — see [`prepare_destination`](#the-helpers-behind-them).

[▲ Back to top](#-table-of-contents)

---

### `rename_file`

The old name of [`move_file`](#move_file) — **the very same function object**, kept so that
code written against `rename_file` keeps working.

**Parameters, returns, raises:** exactly those of [`move_file`](#move_file).

**Example usage:**

```python
rename_file("reports/draft.txt", "reports/final.txt")      # -> <cwd>/reports/final.txt
rename_file is move_file                                   # -> True
```

**Under the hood:**

```python
from .move_file import move_file

rename_file = move_file
```

It is an alias, not a wrapper: a wrapper would be a second `@validate_call` function to
document and test, and an alias cannot drift away from the original. The one visible
consequence is introspection — `rename_file.__name__` is `"move_file"`, so error cards and
tracebacks name the real function. (The [`RenameFile`](../README_FILE_ACTIONS.md#renamefile)
action, by contrast, is a separate class, so that pipeline logs say `RenameFile`.)

[▲ Back to top](#-table-of-contents)

---

### `delete_file`

Deletes a file — or a symlink, **without touching what it points to**.

**Parameters:**

* `path` (*PathLike*): The file or symlink to delete.
* `missing_ok` (*bool*, keyword-only, default `False`): If `True`, a missing path is accepted
  silently.
* `force` (*bool*, keyword-only, default `False`): If `True`, a read-only file is made writable
  first (a problem on Windows, where read-only files cannot be deleted). Off by default —
  removing a protection is an explicit choice.

**Returns:**

* `Path`: The normalized path of the (now deleted) entry.

**Raises:**

* `NotFoundError`: Nothing exists there and `missing_ok=False`.
* `StateError`: The path is a directory (or a special entry) — it is never touched.
* `AccessError`: The OS refuses the deletion.

**Example usage:**

```python
delete_file("cache/old.bin")                    # -> <cwd>/cache/old.bin
delete_file("cache/maybe.bin", missing_ok=True) # no error if it is already gone
delete_file("readonly.txt", force=True)         # clears the read-only flag first (Windows)

delete_file("link.txt")                         # the link goes; the file it pointed to survives
delete_file("dangling_link.txt")                # a dangling link can be deleted too
delete_file("some_folder")                      # raises StateError
```

**Under the hood:**

```python
@validate_call
def delete_file(path, *, missing_ok=False, force=False) -> Path:
    entry = normalize_entry_path(path)                       # "link" means the link itself

    exists = os.path.lexists(entry)                          # a dangling symlink exists as an entry
    is_file_entry = exists and (entry.is_symlink() or entry.is_file())

    if not exists:
        if missing_ok:
            return entry
        raise_file_not_found_error(entry, "delete")
    if not is_file_entry:
        raise_not_a_file_error(entry, "delete")              # a directory is not deleted here

    try:
        entry.unlink()
    except FileNotFoundError:                                # it vanished since the check
        if not missing_ok:
            raise_file_not_found_error(entry, "delete")
    except PermissionError as caught_exc:                    # read-only on Windows
        if not force:
            raise_file_access_error(entry, "delete", caught_exc)
        try:
            if not entry.is_symlink():
                os.chmod(entry, stat.S_IWRITE)               # never the flag of a symlink's TARGET
            entry.unlink()
        except OSError as retry_exc:
            raise_file_access_error(entry, "delete", retry_exc)
    except OSError as caught_exc:
        raise_file_access_error(entry, "delete", caught_exc)

    return entry
```

An earlier version resolved symlinks first, so `delete_file("link")` deleted the **file** the
link pointed to and left a dangling link behind. `normalize_entry_path` resolves only the
folder; the link itself is what `unlink` removes. A directory used to reach `unlink` and
surface as a raw `PermissionError` or `IsADirectoryError`; now it is a clear `StateError`.
A file removed by someone else between the check and the `unlink` is the outcome the caller
wanted with `missing_ok=True` — and an honest "not found" otherwise.

[▲ Back to top](#-table-of-contents)

---

### `backup_file`

Creates a backup copy of a file **next to it**, never overwriting an older backup. The copy is
atomic: a backup is either complete or does not exist.

**Parameters:**

* `path` (*PathLike*): The file to back up.
* `suffix` (*str*, keyword-only, default `".bak"`): Appended to the backup's name. `""` is
  allowed; anything else must be a dot plus at least one character, without separators.
* `timestamp` (*bool*, keyword-only, default `True`): Insert a `YYYYMMDD_HHMMSS` stamp before
  the extension.
* `sync` (*bool*, keyword-only, default `False`): Force the backup to stable storage.

**Returns:**

* `Path`: The normalized path of the **new backup** (not of the original), e.g.
  `report_20261013_142530.txt.bak`.

**Raises:**

* `ParamError`: `suffix` is malformed, or the backup name would equal the source
  (`suffix=""` together with `timestamp=False`).
* `NotFoundError` / `StateError`: The source is missing or is not a regular file.
* `OperationError`: No free numbered name can be found.
* `AccessError`: The OS refuses the copy.

**Example usage:**

```python
backup_file("report.txt")                                  # -> <cwd>/report_20261013_142530.txt.bak
backup_file("report.txt", timestamp=False)                 # -> <cwd>/report.txt.bak
backup_file("report.txt", timestamp=False)                 # again: a numbered variant — nothing is overwritten
backup_file("report.txt", suffix=".orig")                  # -> <cwd>/report_20261013_142530.txt.orig
backup_file("report.txt", suffix="bak")                    # raises ParamError (missing dot)
backup_file("report.txt", suffix="", timestamp=False)      # raises ParamError (the "backup" would be the source)
```

**Under the hood:**

```python
@validate_call
def backup_file(path, *, suffix=".bak", timestamp=True, sync=False) -> Path:
    if not is_valid_suffix(suffix):                          # would produce names like "report.txtbak"
        raise_invalid_suffix_error(suffix, "backup")

    source = resolve_source_file(path, "backup")             # a verified, regular file

    # <stem>[_<timestamp>]<extension><suffix>
    name_parts = [source.stem]
    if timestamp:
        name_parts.append(build_timestamp())
    candidate = source.with_name("_".join(name_parts) + source.suffix + suffix)

    if candidate == source:                                  # no stamp and no suffix: the "backup" is the source
        raise_same_file_error(source, "backup")

    backup_path = make_unique_path(candidate)                # two backups in one second never collide

    try:
        copy_atomically(source, backup_path, sync=sync)      # through a draft
    except OSError as caught_exc:
        raise_file_transfer_error(source, backup_path, "backup", caught_exc)

    return backup_path
```

The stamp has a **one-second** resolution; two backups in the same second used to get the same
name, and the second silently replaced the first. `make_unique_path` turns the second into a
numbered variant, so a backup is never overwritten. An interrupted `shutil.copy2` used to leave
a truncated `.bak` that looked like a real backup — the worst failure a backup can have — which
is why the copy goes through a draft. The name keeps the shape
`<stem>[_<timestamp>]<extension><suffix>`, so existing backups keep the same look, and the
backup lives next to the **real** file (the source is resolved with symlinks followed). The
clock is a separate function (`build_timestamp`) so the format can be tested without patching
time. As with `overwrite=False`, [`make_unique_path`](https://pypi.org/project/simplibs-path/)
only *looks*: another process could create the chosen name before the swap.

[▲ Back to top](#-table-of-contents)

---

### The helpers behind them

The functions share five small internal helpers (not exported). They are worth knowing because
each is the one place where its rule lives.

| Helper                                             | What it does                                                                                       | Used by                                         |
|----------------------------------------------------|----------------------------------------------------------------------------------------------------|-------------------------------------------------|
| `copy_atomically(source, destination, *, sync)`    | Copies through a draft so the destination is the complete copy or untouched.                       | `copy_file`, `backup_file`, `move_across_devices` |
| `prepare_destination(source, destination, operation, *, overwrite)` | Answers "same file? a directory? already there?" once.                       | `copy_file`, `move_file`                        |
| `move_across_devices(source, destination, *, sync)`| The cross-device fallback of a move: atomic copy first, then remove the source.                    | `move_file`                                     |
| `is_cross_device_error(exc)`                       | Recognizes "not on the same disk": `EXDEV` on POSIX, Windows error 17.                             | `move_file`                                     |
| `build_timestamp(now=None)`                        | Formats a moment as a sortable, filename-safe `YYYYMMDD_HHMMSS`; `now` makes the clock testable.   | `backup_file`                                   |

**`copy_atomically`** reuses the three draft helpers of the safe writer, and does what
`shutil.copy2` does — data plus permissions and times — but into a draft:

```python
draft_path = create_draft(destination, append=False)        # a private file next to the destination

try:
    shutil.copyfile(source, draft_path)                     # the data ...
    shutil.copystat(source, draft_path)                     # ... and the permissions and times of the source
    commit_draft(draft_path, destination, keep_mode=False, sync=sync)   # swap it in
except BaseException:
    delete_draft(draft_path)                                # whatever went wrong, no draft is left
    raise
```

`keep_mode=False` stops `commit_draft` from overwriting the copied permissions with the mode of
a destination being replaced.

**`prepare_destination`** is the same four questions for a copy and a move; the caller decides
*how* the paths were normalized (content semantics for a copy, entry semantics for a move):

```python
if str(destination) == str(source):                         # 1. the very same path
    raise_same_file_error(destination, operation)

exists = os.path.lexists(destination)                       # 2. a dangling link counts as existing
is_dir = exists and destination.is_dir() and not destination.is_symlink()
if is_dir:                                                  # 3. a directory is never replaced by a file
    raise_destination_is_dir_error(destination, operation)

if exists and os.path.samefile(source, destination):        # 4. another spelling of the same file
    case_change = operation == "move" and str(destination).casefold() == str(source).casefold()
    if not case_change:                                     #    a hard link, or Windows letter case
        raise_same_file_error(destination, operation)
    return                                                  #    a case-only move is a legitimate rename

if exists and not overwrite:                                # 5. replaced only when the caller allows it
    raise_destination_exists_error(destination, operation)
```

`lexists` matters: a dangling symlink at the destination is an existing **entry**, and a plain
`exists()` would call it free — the later replace would silently remove the link.

**`move_across_devices`** keeps the order that makes it safe:

```python
if source.is_symlink():                                     # a link is an entry pointing somewhere
    raise OSError("A symbolic link cannot be moved to another device.")

copy_atomically(source, destination, sync=sync)             # the copy is complete and in place first ...
source.unlink()                                             # ... only then is the source removed
```

The worst case — the copy is done and the source is locked — leaves **two** files, never none.
Because `move_file` catches this `OSError`, a refused symlink reaches the caller as an
`AccessError` card quoting that message.

[▲ Back to top](#-table-of-contents)

---

[⬅️ Back to main README](../../README.md#-logicoperations--work-with-the-file-itself)
