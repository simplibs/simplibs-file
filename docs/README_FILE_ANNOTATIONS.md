# 🏷️ `annotations` — Shared Annotations

The `annotations` package holds the validatable annotations the whole library shares — the exact types the
functions, actions and the `SafeFileWriter` declare for their parameters. They live in
`simplibs.file.annotations`, so **your own functions can accept exactly what this library accepts**:

```python
from simplibs.file.annotations import ByteCount, EncodingErrors, EncodingName, HashAlgorithm, NewlineMode, TextCollection, WriterMode
```

Each is a plain annotation object — no class to instantiate — and works with `simplibs-validate`
(`@validate_call`) and with type checkers.

```python
from simplibs.path import PathLike
from simplibs.validate import validate_call
from simplibs.file.annotations import ByteCount, EncodingName

@validate_call
def read_head(path: PathLike, *, size: ByteCount = 4096, encoding: EncodingName = "utf-8") -> str:
    with open(path, "rb") as handle:
        return handle.read(size).decode(encoding, errors="replace")

read_head("notes.txt")                          # fine
read_head("notes.txt", size=0)                  # raises ValidationError — a read of zero bytes is never meant
read_head("notes.txt", encoding="rot13")        # raises ValidationError — not a text encoding
```

The same annotations are what the actions use for their constructor options, so a mistake is
caught **before** any file is touched: `ReadText(encoding="rot13")` and `FileHash(chunk_size=0)`
are a `ValidationError` at construction.

## Two kinds of annotation

| Kind                | Annotations                                                         | How it decides                                                       |
|---------------------|---------------------------------------------------------------------|----------------------------------------------------------------------|
| **Annotated type**  | `ByteCount`, `EncodingName`, `TextCollection`                       | `Annotated[base, predicate]` — a base type (`int`, `str`) plus a predicate that checks the **value**. |
| **Fixed set**       | `EncodingErrors`, `NewlineMode`, `HashAlgorithm`, `WriterMode`      | A `Literal` — only the listed values exist.                           |

A fixed set fails at the signature on a typo (`errors="ignroe"`) instead of months later, when a
bad character is finally met.

Both kinds are written so that editors and type checkers understand them: a fixed set is a
`Literal`, a checked type is `typing.Annotated[base, predicate]` — to the editor it is the plain
base type, while `@validate_call` reads the predicate from the metadata and checks the value.

## Where each one is used

| Annotation       | Parameter                  | Used by                                                                                      |
|------------------|----------------------------|----------------------------------------------------------------------------------------------|
| `EncodingName`   | `encoding`                 | every text reader and writer, `is_text_file`, `SafeFileWriter` — and their actions           |
| `EncodingErrors` | `errors`                   | every text reader and writer except `write_json`, `SafeFileWriter`                           |
| `NewlineMode`    | `newline`                  | every text writer (`write_text`, `write_lines`, `write_aggregated`, `write_json`, `append_text`), `SafeFileWriter` |
| `ByteCount`      | `chunk_size`, `sample_size`| `file_hash`, `is_text_file`                                                                  |
| `HashAlgorithm`  | `algorithm`                | `file_hash`                                                                                  |
| `TextCollection` | `lines`, `parts`           | `write_lines`, `write_aggregated` — and their actions                                        |
| `WriterMode`     | `mode`                     | `SafeFileWriter`                                                                             |

> **Rules check by hand.** `IsTextFile` and `ContentIs` are classes, not `@validate_call`
> functions, so they call the predicates behind `ByteCount` and `EncodingName` directly — and
> report an unusable parameter as a **`ParamError`** when the rule is built. The annotations
> raise a **`ValidationError`** at a call or an action's construction. The predicates
> (`is_byte_count`, `is_text_encoding`) live in the package's private `_helpers` and are not
> exported.

---

## 🧭 Table of Contents

**Annotated types**

* [`ByteCount`](#bytecount)
* [`EncodingName`](#encodingname)
* [`TextCollection`](#textcollection)

**Fixed sets**

* [`EncodingErrors`](#encodingerrors)
* [`NewlineMode`](#newlinemode)
* [`HashAlgorithm`](#hashalgorithm)
* [`WriterMode`](#writermode)

[⬅️ Back to main README](../README.md#-annotations--shared-validatable-annotations)

---

### `ByteCount`

A **positive number of bytes** — a read chunk, a sample size.

**Definition:**

```python
ByteCount = Annotated[int, is_byte_count]
```

**Accepts:** `1`, `4096`, `8192`, `1_048_576` — any `int` greater than zero.

**Rejects:** `0`, negative integers, `True` / `False`, `None`, non-numbers (`"x"`).

**Example usage:**

```python
FileHash(chunk_size=65_536)             # fine
FileHash(chunk_size=0)                  # raises ValidationError
IsTextFile(sample_size=-1)              # raises ParamError — a rule checks by hand, see above

@validate_call
def sample(path: PathLike, size: ByteCount = 8192) -> bytes: ...
```

**Why it cannot be zero.** `chunk_size=0` would make a read loop spin forever and
`sample_size=-1` would quietly read the whole file; both are stopped at the signature with
the library's usual card.

**Why `bool` is rejected.** In Python `True` is an `int` (it equals `1`), but `chunk_size=True`
is never what a caller meant.

<details>
<summary>🔍 Under the hood</summary>

```python
def is_byte_count(value: int) -> bool:
    # 1. A real integer (a bool is an int in Python, but never what the caller meant)
    if not isinstance(value, int) or isinstance(value, bool):
        return False

    # 2. At least one byte
    return value > 0
```

</details>

[▲ Back to top](#-table-of-contents)

---

### `EncodingName`

The **name of a text encoding** Python can both encode **and** decode with.

**Definition:**

```python
EncodingName = Annotated[str, is_text_encoding]
```

**Accepts:** `"utf-8"`, `"utf-8-sig"`, `"utf-16"`, `"cp1250"`, `"ascii"`, `"latin-1"` — and any
other name Python knows as a text codec (aliases such as `"UTF8"` included).

**Rejects:** unknown names (`"no-such-codec"`), blank strings (`""`, `"   "`), non-text codecs
(`"rot13"`, `"base64"`, `"hex"`), non-strings.

**Example usage:**

```python
ReadText(encoding="cp1250")             # fine
ReadText(encoding="rot13")              # raises ValidationError — before any file is touched

@validate_call
def convert(text: str, encoding: EncodingName = "utf-8") -> bytes:
    return text.encode(encoding)
```

**Why not just `codecs.lookup`.** `codecs.lookup("rot13")` and `codecs.lookup("base64")` succeed,
but they are str-to-str and bytes-to-bytes transforms: `"x".encode("rot13")` fails only at the
moment of the real write — after the draft file was created. The check **probes both
directions** with empty data, which is exactly what a real read or write will need.

**Why a `ValidationError`, not a `ParamError`.** A rejected name is a wrong *value* of an
argument — like a blank `PathLike` — and is reported the same way.

<details>
<summary>🔍 Under the hood</summary>

```python
def is_text_encoding(name: str) -> bool:
    # 1. Only a non-blank string can be an encoding name
    if not isinstance(name, str) or not name.strip():
        return False

    # 2. Probe both directions with empty data — this is what a real read/write will need
    try:
        "".encode(name)
        b"".decode(name)

    # 3. Unknown names, bytes-to-bytes codecs, embedded null characters
    except (LookupError, UnicodeError, ValueError):
        return False

    # 4. Both directions work
    return True
```

</details>

[▲ Back to top](#-table-of-contents)

---

### `TextCollection`

A **collection of texts** — lines, fragments — and never a single text.

**Definition:**

```python
TextCollection = Annotated[Collection[str], is_text_collection]
```

**Accepts:** `["a", "b"]`, `("a",)`, `{"a"}`, `[]` — any list, tuple or set whose every item is a `str`.

**Rejects:** a bare string (`"abc"`), `bytes`, generators and iterators, collections with a non-`str`
item (`[1, 2]`, `["a", None]`), `None`.

**Example usage:**

```python
write_lines("out.txt", ["a", "b"])              # fine
write_lines("out.txt", "abc")                   # raises ValidationError — not three lines "a", "b", "c"
WriteAggregated(path="out.txt")(["x", "y"])     # fine
WriteLines(path="out.txt")([1, 2])              # raises ValidationError
```

**Why a bare string is rejected.** In Python a string is a collection of one-character strings, so
a plain `Collection[str]` would accept `"abc"` and write three lines. That is the usual result of
a forgotten list, and it is stopped at the signature.

**Why not an iterable.** The writers use the items twice and the check walks them once more, so a
generator would arrive empty. A collection can be walked repeatedly.

<details>
<summary>🔍 Under the hood</summary>

```python
def is_text_collection(value: Collection[str]) -> bool:
    # 1. A text is technically a collection of one-character texts — never what the caller meant
    if isinstance(value, (str, bytes, bytearray)):
        return False

    # 2. A real collection: it has a length and can be walked more than once (not a generator)
    if not isinstance(value, Collection):
        return False

    # 3. Every item is text
    return all(isinstance(item, str) for item in value)
```

</details>

[▲ Back to top](#-table-of-contents)

---

### `EncodingErrors`

How to treat characters or bytes that **do not fit the encoding** — the error handlers that work
**in both directions** (encoding and decoding).

**Definition:**

```python
EncodingErrors = Literal[
    "strict",
    "ignore",
    "replace",
    "backslashreplace",
    "surrogateescape",
    "surrogatepass",
]
```

| Value                | What it does                                                                          |
|----------------------|---------------------------------------------------------------------------------------|
| `"strict"` (default) | Raise a `ConversionError` on the first problem.                                       |
| `"ignore"`           | Drop what does not fit.                                                               |
| `"replace"`          | Substitute a placeholder: `?` when encoding, `�` (U+FFFD) when decoding.              |
| `"backslashreplace"` | Substitute a backslash escape (`\xe8`, `\u010d`).                                     |
| `"surrogateescape"`  | Carry undecodable bytes through as lone surrogates, so they can be written back unchanged. |
| `"surrogatepass"`    | Let lone surrogates through the UTF codecs.                                           |

**Rejects:** everything else — `"xmlcharrefreplace"`, `"namereplace"`, a typo (`"ignroe"`), `None`.

**Example usage:**

```python
ReadText(errors="replace")("damaged.txt")                       # b'a\xffb'  ->  'a\ufffdb'
WriteText(path="out.txt", encoding="ascii", errors="replace")("č")     # file holds b'?'
WriteText(path="out.txt", encoding="ascii")("č")                # raises ConversionError — and the old file is intact
WriteText(path="out.txt", errors="xmlcharrefreplace")           # raises ValidationError
```

**Why not all handlers.** `xmlcharrefreplace` and `namereplace` are **encode-only**: used while
decoding they raise a bare `TypeError` from inside the codec machinery. One literal shared by
reads and writes must contain only handlers that are safe for both.

**Why not a free `str`.** A typo would only fail when a bad character is finally met — possibly
months later. The literal fails immediately.

[▲ Back to top](#-table-of-contents)

---

### `NewlineMode`

The **line ending** a text write produces.

**Definition:**

```python
NewlineMode = Literal["\n", "\r\n", "\r"] | None
```

| Value            | Line ending                                                  |
|------------------|--------------------------------------------------------------|
| `"\n"` (default) | Unix / the library's own default.                            |
| `"\r\n"`         | Windows.                                                     |
| `"\r"`           | Old Mac.                                                     |
| `None`           | The line ending of the **current platform** (`os.linesep`).  |

**Rejects:** every other string (`"\t"`, `"\n\n"`, `""`) and non-strings.

**Example usage:**

```python
WriteText(path="out.txt")("a\nb")                       # file: b'a\nb'
WriteText(path="out.txt", newline="\r\n")("a\nb")       # file: b'a\r\nb'
WriteLines(path="out.txt", newline="\r")(["a", "b"])    # file: b'a\rb\r'
WriteText(path="out.txt", newline=None)("a\nb")         # whatever this platform uses
```

**Why a default and not the platform.** Python's text mode silently writes `\r\n` on Windows, so
the same program produces different bytes on different machines. The library defaults to
`"\n"` and makes every other choice **explicit** — `None` is the platform behaviour, and a caller
has to ask for it.

**Same meaning as `open(newline=...)` on writes.** Every `"\n"` in the text becomes the chosen
ending; an existing `"\r\n"` is therefore not "recognized" and would become `"\r\r\n"`. Text that
already has its own line endings should be written as bytes (`WriteBytes`).

**Writes only.** The readers do not take it: `ReadText` always normalizes `"\r\n"` and `"\r"` to
`"\n"`, and `ReadLines(keep_ends=True)` keeps the original endings.

[▲ Back to top](#-table-of-contents)

---

### `HashAlgorithm`

A **fixed-length hash algorithm** guaranteed by `hashlib`.

**Definition:**

```python
HashAlgorithm = Literal[
    "md5", "sha1",
    "sha224", "sha256", "sha384", "sha512",
    "sha3_224", "sha3_256", "sha3_384", "sha3_512",
    "blake2b", "blake2s",
]
```

**Accepts:** exactly the twelve names above (lowercase).

**Rejects:** `"shake_128"`, `"shake_256"`, `"crc32"`, `"SHA256"`, anything else.

**Example usage:**

```python
FileHash()("archive.zip")                       # "sha256" is the default
FileHash(algorithm="blake2b")("archive.zip")
FileHash(algorithm="crc32")                     # raises ValidationError
```

**`md5` and `sha1` are for change detection and checksums only, never for security.** Because
the library offers them for that purpose alone, `file_hash` declares them non-security
(`usedforsecurity=False`), which keeps them working on FIPS-restricted systems where a plain
`hashlib.md5()` raises.

**Why not `hashlib.algorithms_guaranteed`.** That set contains `shake_128` and `shake_256`, whose
digest needs an explicit length — `hexdigest()` without one raises. They are left out instead of
growing a `length` parameter nobody asked for.

[▲ Back to top](#-table-of-contents)

---

### `WriterMode`

The **open modes `SafeFileWriter` supports**: overwrite or append, text or binary.

**Definition:**

```python
WriterMode = Literal["w", "wb", "a", "ab"]
```

| Value    | Meaning                          |
|----------|----------------------------------|
| `"w"`    | Overwrite, text.                 |
| `"wb"`   | Overwrite, binary.               |
| `"a"`    | Append, text.                    |
| `"ab"`   | Append, binary.                  |

**Rejects:** `"x"`, `"r"`, `"r+"`, `"w+"`, `"wt"`, anything else.

**Example usage:**

```python
with SafeFileWriter("out/data.bin", mode="wb") as handle:
    handle.write(b"\x00\xff")                   # replaces the file atomically when the block ends

SafeFileWriter("out/data.bin", mode="x")        # raises ValidationError
```

**Why exactly four modes.** The old `mode: str` accepted `"x"` and `"r+"` and silently behaved as
`"w"`. A literal of exactly the supported modes turns that into an immediate, readable error.
Exclusive creation and in-place update contradict the draft-and-swap idea — the target is only
ever replaced **as a whole**.

[▲ Back to top](#-table-of-contents)

---

[⬅️ Back to main README](../README.md#-annotations--shared-validatable-annotations)
