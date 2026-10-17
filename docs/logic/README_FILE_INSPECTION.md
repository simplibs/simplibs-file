# 🔎 `logic/inspection` — Ask a File About Itself

The `inspection` package holds the functions that **ask a file a question** — how big it is, what
its content hashes to, whether it looks like text — without changing anything. Two of them are
**strict**: they raise a structured card when there is no file to ask. The third is a
**predicate**: it answers `False` instead of raising.

```python
from simplibs.file import file_hash, file_size, is_text_file
```

Every function accepts its path as a [`PathLike`](../README_FILE_ANNOTATIONS.md) — a non-blank
`str` or a `Path` — and is wrapped in `@validate_call`, so a blank string or a wrong type is
rejected with a `ValidationError` before the body runs. Each has an
[action](../README_FILE_ACTIONS.md#inspection) counterpart for pipelines — except the predicate,
whose counterpart is the [`IsTextFile`](../README_FILE_RULES.md#istextfile) rule.

## Strict or never-raising

| Function       | Returns | A missing file …                   | Use it when …                                          |
|----------------|---------|------------------------------------|--------------------------------------------------------|
| `file_size`    | `int`   | raises `NotFoundError`             | a number is needed and "no file" is an error           |
| `file_hash`    | `str`   | raises `NotFoundError`             | a digest is needed and "no file" is an error           |
| `is_text_file` | `bool`  | is `False` — never raises          | a **filter** over thousands of paths must not stop on one bad entry |

"The size of nothing" has no honest number, which is why the first two are strict. A scan that
asks the same question of every entry wants the opposite — hence the predicate, and the rules
[`SizeIs`](../README_FILE_RULES.md#sizeis) and [`IsTextFile`](../README_FILE_RULES.md#istextfile)
built on never-raising twins of these functions.

## A note on what is read

* `file_size` makes **one `stat`** and reads no content.
* `file_hash` reads the whole file, but in **chunks**, so memory use is flat for a file of any size.
* `is_text_file` reads only the **first `sample_size` bytes**.

The two strict functions follow a symlink (the **content** behind it is what is measured), and
need a **regular file**: a directory is a `StateError`, not a number.

## A note on timing

Every answer holds **at the moment of the call**. A file can grow, change or disappear right
after. Use these as fail-fast checks and as change detection, not as a lock.

## A note on the folder name

The folder is called `inspection`, not `inspect`, because `inspect` is the name of a standard-library
module. A script run from the folder's *parent*, or a test runner that puts that parent on
`sys.path`, would let a folder called `inspect` shadow the stdlib module and break everything that
imports it (for example `dataclasses`). The error cards still say `"inspect"` — that is only the name
of the operation in a text.

---

## 🧭 Table of Contents

* [`file_size`](#file_size)
* [`file_hash`](#file_hash)
* [`is_text_file`](#is_text_file)

[⬅️ Back to main README](../../README.md#-logicinspection--ask-a-file-about-itself)

---

### `file_size`

Gets the size of a file in bytes — without reading it.

**Parameters:**

* `path` (*PathLike*): The file to measure. A symlink is followed.

**Returns:**

* `int`: The size in bytes (`0` for an empty file).

**Raises:**

* `NotFoundError`: The file does not exist.
* `StateError`: The path is not a regular file.
* `AccessError`: The OS refuses to report the size.

**Example usage:**

```python
file_size("archive.zip")        # -> 1048576
file_size("empty.txt")          # -> 0
file_size("word.txt")           # -> 9      (a file holding "Příliš": bytes, not characters)
file_size("missing.txt")        # raises NotFoundError
file_size("some_folder")        # raises StateError
```

**Under the hood:**

```python
@validate_call
def file_size(path: PathLike) -> int:
    source = resolve_source_file(path, "inspect")        # normalized, and a regular file

    try:
        return source.stat().st_size                     # one stat, no content read
    except OSError as caught_exc:
        raise_file_access_error(source, "inspect", caught_exc)
```

The number is the **logical** length of the content, as `ls -l` shows it. Sparse files and
compression make the space actually used on disk differ. It is also the number behind the
[`SizeIs`](../README_FILE_RULES.md#sizeis) rule — for filtering prefer the rule, which does not
raise on a missing file.

[▲ Back to top](#-table-of-contents)

---

### `file_hash`

Computes the hash of a file's content, reading it in chunks.

**Parameters:**

* `path` (*PathLike*): The file to hash. A symlink is followed.
* `algorithm` (*HashAlgorithm*, keyword-only, default `"sha256"`): One of `md5`, `sha1`, `sha224`,
  `sha256`, `sha384`, `sha512`, `sha3_224`, `sha3_256`, `sha3_384`, `sha3_512`, `blake2b`,
  `blake2s`. `md5` and `sha1` are for change detection and checksums only, never for security.
* `chunk_size` (*ByteCount*, keyword-only, default `1_048_576`): How many bytes to read at a
  time — a positive `int`. The default of 1 MiB keeps memory flat for a file of any size.

**Returns:**

* `str`: The digest as a lowercase hexadecimal string.

**Raises:**

* `NotFoundError`: The file does not exist.
* `StateError`: The path is not a regular file.
* `AccessError`: The OS refuses the read.

**Example usage:**

```python
file_hash("archive.zip")                        # -> 'b5bb9d8014a0f9b1...'  (64 hex characters)
file_hash("a.txt", algorithm="md5")             # -> '5d41402abc4b2a76b9719d911017c592'
file_hash("big.iso", chunk_size=16_777_216)     # larger chunks, fewer reads

if file_hash("config.json") != stored_digest:   # change detection: skip the work if nothing changed
    rebuild()
```

**Under the hood:**

```python
@validate_call
def file_hash(path, *, algorithm="sha256", chunk_size=1_048_576) -> str:
    source = resolve_source_file(path, "hash")

    # the two legacy algorithms are marked "not for security", so they also work on FIPS-restricted systems
    legacy = algorithm in ("md5", "sha1")
    digest = hashlib.new(algorithm, usedforsecurity=not legacy)

    try:
        with source.open("rb") as handle:
            while chunk := handle.read(chunk_size):         # flat memory
                digest.update(chunk)
    except OSError as caught_exc:
        raise_file_access_error(source, "hash", caught_exc)

    return digest.hexdigest()
```

Built for change detection and de-duplication in extraction pipelines: hash a file, compare with
the stored value, skip unchanged work. **Content only** — the path and the metadata are not part
of the hash, so two identical files in different folders hash equal. Declaring `md5` and `sha1`
as non-security (`usedforsecurity=False`) is honest for this purpose and keeps them working where
a plain `hashlib.md5()` raises. The `shake_*` algorithms are not offered: a variable-length
digest needs a length, which nobody asked for.

[▲ Back to top](#-table-of-contents)

---

### `is_text_file`

Checks whether a file **looks like text**, judging by its first bytes — and never raises for a
disk problem.

**Parameters:**

* `path` (*PathLike*): The file to check.
* `sample_size` (*ByteCount*, keyword-only, default `8192`): How many bytes from the start to inspect.
* `encoding` (*EncodingName*, keyword-only, default `"utf-8"`): The encoding the text is expected to have.
* `_validate_call` (*bool*, keyword-only, default `True`): Internal bypass switch for
  `@validate_call` — the [`IsTextFile`](../README_FILE_RULES.md#istextfile) rule passes `False`
  because it has already checked the input. Ordinary callers can ignore it.

**Returns:**

* `bool`: `True` for an **empty file**, or a regular file whose first `sample_size` bytes decode
  in `encoding` and contain no NUL character. `False` for everything else — a missing path, a
  directory, an unreadable file, undecodable bytes, binary content.

**Example usage:**

```python
is_text_file("src/a.py")                        # -> True
is_text_file("logo.png")                        # -> False
is_text_file("empty.txt")                       # -> True    (as `file` and Git treat it)
is_text_file("missing.txt")                     # -> False   (no exception)
is_text_file("export.txt", encoding="utf-16")   # -> True for a UTF-16 file; False with the default
is_text_file(5)                                 # raises ValidationError — a wrong TYPE is still an error
```

**Under the hood:**

```python
# 1. read the sample; any refusal of the OS or of path handling is a plain "no"
try:
    candidate = normalize_path(path)
    if not candidate.is_file():
        return False
    with candidate.open("rb") as handle:
        sample = handle.read(sample_size)
except (OSError, ValueError, SimpleException):
    return False

# 2. an empty file is text by convention
if not sample:
    return True

# 3. decode incrementally: a multi-byte character cut by the end of the sample is not an error —
#    unless the sample is the whole file
decoder = codecs.getincrementaldecoder(encoding)(errors="strict")
try:
    text = decoder.decode(sample, final=len(sample) < sample_size)
except UnicodeDecodeError:
    return False

# 4. a NUL character is the classic mark of binary content (a NUL BYTE is fine in UTF-16/32 text)
return "\x00" not in text
```

A **heuristic**, honestly: only the first `sample_size` bytes are judged. A binary file whose
first 8 KB happen to be valid text passes; a text file with a NUL at the 9th kilobyte passes too.
The two cheap, decisive signals are that the sample must decode and must not contain a NUL
**character**. The NUL is looked for in the *decoded* text, not in the bytes — a NUL *byte* is
normal in UTF-16 and UTF-32, so searching the bytes would call such files binary.

[▲ Back to top](#-table-of-contents)

---

[⬅️ Back to main README](../../README.md#-logicinspection--ask-a-file-about-itself)
