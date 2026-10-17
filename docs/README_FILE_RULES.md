# 📐 `rules` — Rules for Files

The `rules` package holds `Rule` classes that judge a file by what is **inside** it or by a
**measurable property** of it — its content and its size. Every one is a real `Rule` from
[`simplibs-rules`](https://pypi.org/project/simplibs-rules/), so it composes with `&`, `|`
and `~`, describes itself, and explains its failures.

```python
from simplibs.file.rules import ContentIs, IsTextFile, SizeIs
```

The questions *"does it exist?"*, *"is it a file?"*, *"what is it called?"* belong to the
[path rules](https://pypi.org/project/simplibs-path/) (`IsFile`, `HasSuffix`, `NameIs`, ...).
These three start where they stop — and are meant to be combined with them:

```python
from simplibs.path.rules import IsFile, HasSuffix, IsHidden
from simplibs.rules.predicates.comparisons import GreaterThan

source_files = IsFile() & IsTextFile() & HasSuffix(".py") & ~IsHidden() & SizeIs(GreaterThan(0))
```

Rules are **not** exported from `simplibs.file` itself — they are a domain of their own,
imported through `simplibs.file.rules`, which defines `__all__`.

## Where rules are used

```python
from simplibs.path import collect_files
from simplibs.rules.predicates.comparisons import GreaterThan, InRange
from simplibs.rules.predicates.strings import StartsWith

# 1. As scanner filters
collect_files("project", include_filter=IsTextFile() & SizeIs(GreaterThan(0)))
collect_files("project", exclude_filter=SizeIs(GreaterThan(1_000_000)))

# 2. As validation of your own function arguments (simplibs-validate)
TextFile = Annotated[Path, IsTextFile()]

@validate_call
def process(source: TextFile) -> None: ...

# 3. As pipeline gates (simplibs-actions) — a rule becomes a pass-through guard step
pipeline = IsTextFile() >> ReadText() >> WriteText(path="out/copy.txt")

# 4. Directly
ContentIs(StartsWith("#!")).is_valid("scripts/run.sh")      # -> True
SizeIs(InRange(1, 100)).validate("huge.bin")                # raises a ValidationError card
```

## What every rule here guarantees

* **`is_valid` returns a strict `bool` and never raises.** Anything that cannot be a path
  (`None`, a number, a blank string, a string with a null byte) **and** anything the disk
  cannot answer — a missing file, a directory, no permission, bytes that do not decode —
  simply fails the rule.
* **`describe()` is a short noun phrase** that containers compose into readable text:
  `(IsFile() & SizeIs(GreaterThan(0))).describe()` → `"existing file & size: > 0"`.
* **The failure card says what is wrong.** A value that is not a path gives a `TypeError`
  card, a blank string a `ValueError` card, a file that cannot be read says so, and a file
  whose measured part fails the check gives the card of the rule that judged it.
* **Constructor mistakes are `ParamError`s**, raised when the rule is built, not when it is
  first used (a non-callable operand, an invalid encoding, a non-positive byte count).
  The options are **keyword-only** (`IsTextFile(sample_size=100)`, never `IsTextFile(100)`).
* **Nothing is read that is not needed.** `SizeIs` makes one `stat`; `IsTextFile` and
  `ContentIs` read only the **beginning** of the file, so a scan over thousands of files
  does not read each one whole.
* **`~Rule()` accepts what has no answer.** A missing file has no size, so `SizeIs(...)`
  fails on it and `~SizeIs(...)` passes. Where the distinction matters, put `IsFile()` in
  front: `IsFile() & ~SizeIs(GreaterThan(0))`.

## Two kinds of rule

| Kind          | Rules                      | What it does                                                                  |
|---------------|----------------------------|-------------------------------------------------------------------------------|
| **Predicate** | `IsTextFile`               | Asks one fixed question about the file and answers yes or no.                 |
| **Lens**      | `SizeIs`, `ContentIs`      | Reads **one part** of the file and lets **another rule** judge that part.      |

A lens needs no comparison logic of its own: `SizeIs(GreaterThan(0))`, `SizeIs(InRange(1, 1024))`
and `ContentIs(StartsWith("#!"))` reuse the numeric and string rules of `simplibs-rules`, so
the **whole** vocabulary of those rules applies to a file's size and content. A plain
callable works too: `SizeIs(lambda size: size <= 5 * 1024 * 1024)` is wrapped so that it can
describe itself and explain a failure.

Both lenses share one base class (`FilePartIs`), exactly as `NameIs`, `StemIs` and
`ParentNameIs` share `PathPartIs`: the rule that **fails** explains the failure — see
[How a lens fails](#how-a-lens-fails).

## How a lens fails

When the wrapped rule rejects the part, the failure card is **the wrapped rule's own**,
about the part, labelled `<value_name>.<part>`:

```python
SizeIs(LessThan(10)).validate("big.bin", value_name="source")
# ValidationError — LESS_THAN_ERROR
#   label:    source.size
#   problem:  Value 50 is not less than 10.
```

Consequently `exc.value` is the **part** (`50`), not the path. When the part could not be
read at all (the file is missing, is a directory, is unreadable, or does not decode), the
wrapped rule is **not asked** — the card says so instead:

```python
ContentIs(StartsWith("#!")).validate("missing.sh", value_name="source")
# ValidationError — FILE_CONTENT_IS_ERROR
#   problem:  The content of 'missing.sh' cannot be read (it is missing, is not a regular
#             file, is unreadable, or does not decode).
#   how_to_fix: Provide a path to an existing, readable file.
```

---

## 🧭 Table of Contents

* [`IsTextFile`](#istextfile)
* [`SizeIs`](#sizeis)
* [`ContentIs`](#contentis)

[⬅️ Back to main README](../README.md#-rules--rules-for-files)

---

### `IsTextFile`

The path must be a readable file whose **beginning looks like text** — the first gate of an
extraction pipeline, so a renamed image or a compiled `.pyc` never reaches the decoder.

**Parameters:**

* `sample_size` (*ByteCount*, keyword-only, default `8192`): How many bytes from the start
  to inspect. A positive `int` (zero, negatives and `bool` are a `ParamError`).
* `encoding` (*EncodingName*, keyword-only, default `"utf-8"`): The encoding the text is
  expected to have. An unknown name or a non-text codec (`"rot13"`) is a `ParamError`.

**`describe()`:** `"text file"` — always, whatever the parameters.

**Example usage:**

```python
IsTextFile().is_valid("src/a.py")                       # -> True
IsTextFile().is_valid("logo.png")                       # -> False  (undecodable / contains NUL)
IsTextFile().is_valid("empty.txt")                      # -> True   (an empty file counts as text)
IsTextFile().is_valid("missing.txt")                    # -> False  (never raises)
IsTextFile(encoding="utf-16").is_valid("export.txt")    # -> True   (for a UTF-16 file)

include_filter = IsTextFile() & HasSuffix(".py", ".md")
```

**Notes.** A **heuristic**, honestly: only the first `sample_size` bytes are judged. They must
decode in `encoding` and contain no NUL **character**, so a binary file whose first 8 KB
happen to be valid text passes, and a text file with a NUL deep inside it passes too. The
NUL is searched in the *decoded* text, which is why UTF-16 and UTF-32 text — full of NUL
*bytes* — is still recognized as text. A multi-byte character cut by the end of the sample is
not an error. The failure card says what was checked (`... or its beginning is binary or not
valid utf-8`), so the verdict is explainable. Error name: `IS_TEXT_FILE_ERROR`.

<details>
<summary>🔍 Under the hood</summary>

```python
from simplibs.path.tools import build_path_rule_exception, to_path


class IsTextFile(Rule):
    __slots__ = ("sample_size", "encoding")

    def __init__(self, *, sample_size: int = 8192, encoding: str = "utf-8") -> None:
        if not is_byte_count(sample_size):
            raise_rule_param_invalid_error("IsTextFile", "sample_size", sample_size, "a positive int (a number of bytes)")
        if not is_text_encoding(encoding):
            raise_rule_param_invalid_error("IsTextFile", "encoding", encoding, "the name of a text encoding (e.g. 'utf-8')")
        self.sample_size = sample_size
        self.encoding = encoding

    def is_valid(self, value) -> bool:
        path = to_path(value)                    # anything that is not a usable path fails
        if path is None:
            return False
        return is_text_file(path, sample_size=self.sample_size, encoding=self.encoding, _validate_call=False)
```

And the function it delegates to:

```python
# 1. read the sample; any refusal is a plain "no"
try:
    candidate = normalize_path(path)
    if not candidate.is_file():
        return False
    with candidate.open("rb") as handle:
        sample = handle.read(sample_size)
except (OSError, ValueError, SimpleException):
    return False

# 2. an empty file is text by convention (as `file` and Git treat it)
if not sample:
    return True

# 3. decode incrementally — a character cut by the end of the sample is not an error
decoder = codecs.getincrementaldecoder(encoding)(errors="strict")
try:
    text = decoder.decode(sample, final=len(sample) < sample_size)
except UnicodeDecodeError:
    return False

# 4. a NUL character is the classic mark of binary content
return "\x00" not in text
```

</details>

[▲ Back to top](#-table-of-contents)

---

### `SizeIs`

The **size of the file, in bytes**, must satisfy another rule — "non-empty files only",
"skip anything over 1 MB" — without a single new comparison.

**Parameters:**

* `rule` (*Rule | Callable[[int], bool]*): Judges the size as an `int`. A plain callable is
  wrapped so it can describe itself and explain a failure. A non-callable is a `ParamError`.

**`describe()`:** `"size: <rule>"` — a compound operand is parenthesized:
`"size: (> 5 | < 2)"`.

**Example usage:**

```python
SizeIs(GreaterThan(0)).is_valid("src/a.py")             # -> True   (non-empty)
SizeIs(GreaterThan(0)).is_valid("empty.txt")            # -> False
SizeIs(InRange(1, 1_000_000)).is_valid("data.csv")      # -> True   (describe: "size: in [1, 1000000]")
SizeIs(lambda size: size <= 5 * 1024 * 1024).is_valid("upload.zip")

collect_files("project", include_filter=IsFile() & SizeIs(GreaterThan(0)))
collect_files("project", exclude_filter=SizeIs(GreaterThan(10_000_000)))
validate(upload, SizeIs(LessThan(5_000_000)))
```

**Notes.** One `stat`, no content read. A path **without a size** — a missing path, a
directory, a file the OS will not answer for — fails the rule, and a symlink to a file
reports the **target's** size. A size of `0` is a real size (an empty file passes
`SizeIs(Equals(0))`), not a missing one. On failure the card is the wrapped rule's own,
labelled `<value_name>.size`; when no size exists the error name is `FILE_SIZE_IS_ERROR`.
The strict twin is the [`FileSize`](README_FILE_ACTIONS.md#filesize) action, which raises
when there is no file.

<details>
<summary>🔍 Under the hood</summary>

```python
class SizeIs(FilePartIs):
    __slots__ = ()
    _part_name = "size"

    def _read_part(self, path):
        return read_file_size(path)              # an int, or None for anything that has no size
```

The size reader never raises — `None` is the one non-`int` answer:

```python
def read_file_size(path: Path) -> int | None:
    try:
        if not path.is_file():
            return None
        return path.stat().st_size               # one stat, no content read
    except (OSError, ValueError):
        return None
```

And the shared base decides the verdict:

```python
def is_valid(self, value) -> bool:
    path = to_path(value)
    if path is None:
        return False
    part = self._read_part(path)
    if part is None:                             # no part -> the wrapped rule is not even asked
        return False
    return bool(self.rule.is_valid(part))
```

</details>

[▲ Back to top](#-table-of-contents)

---

### `ContentIs`

The **beginning of a file's text** must satisfy another rule — "executable scripts"
(`StartsWith("#!")`), "files that mention TODO near the top", "files with a license header".

**Parameters:**

* `rule` (*Rule | Callable[[str], bool]*): Judges the decoded text as a string. A plain
  callable is wrapped so it can describe itself and explain a failure.
* `encoding` (*EncodingName*, keyword-only, default `"utf-8-sig"`): So a BOM never spoils
  `StartsWith`.
* `max_bytes` (*ByteCount*, keyword-only, default `65_536`): How many bytes from the start
  the wrapped rule gets to see.

**`describe()`:** `"content: <rule>"` — e.g. `"content: string starting with '#!'"`; a
compound operand is parenthesized.

**Example usage:**

```python
ContentIs(StartsWith("#!")).is_valid("scripts/run.sh")           # -> True
ContentIs(Contains("TODO")).is_valid("src/a.py")                 # -> True if it appears in the first 64 KiB
ContentIs(Equals("")).is_valid("empty.txt")                      # -> True   (an empty file has empty content)
ContentIs(Equals("č"), encoding="cp1250").is_valid("legacy.txt")
ContentIs(Contains("TODO"), max_bytes=1_000_000).is_valid("big_module.py")   # look further

scripts = collect_files("project", include_filter=ContentIs(StartsWith("#!")))
gate = IsFile() & ContentIs(StartsWith("# Copyright"))
```

**Notes.** The wrapped rule sees only the first `max_bytes` (64 KiB by default), decoded.
That is part of the contract: `Contains("x")` can miss an `x` after the first `max_bytes`,
while `StartsWith` and header checks are unaffected — raise `max_bytes` when the whole
content matters. Reading rules:

* **Line endings are normalized** to `"\n"`, as `ReadText` does.
* **A BOM is removed** with the default encoding (`"utf-8"` would keep it as `"\ufeff"`).
* **A character cut at `max_bytes` is not an error** — unless the head is the whole file.
* **Undecodable bytes** make the rule fail — even for a callable that accepts anything. It
  does not raise.

On failure the card is the wrapped rule's own, labelled `<value_name>.content`; when the
content could not be read the error name is `FILE_CONTENT_IS_ERROR`.

<details>
<summary>🔍 Under the hood</summary>

```python
class ContentIs(FilePartIs):
    __slots__ = ("encoding", "max_bytes")
    _part_name = "content"

    def __init__(self, rule, *, encoding: str = "utf-8-sig", max_bytes: int = 65_536) -> None:
        if not is_text_encoding(encoding):
            raise_rule_param_invalid_error("ContentIs", "encoding", encoding, "the name of a text encoding (e.g. 'utf-8-sig')")
        if not is_byte_count(max_bytes):
            raise_rule_param_invalid_error("ContentIs", "max_bytes", max_bytes, "a positive int (a number of bytes)")
        super().__init__(rule)                   # the wrapped rule is validated by the base
        self.encoding = encoding
        self.max_bytes = max_bytes

    def _read_part(self, path):
        return read_file_head(path, max_bytes=self.max_bytes, encoding=self.encoding)
```

The head reader never raises — `None` means "could not be read", `""` is a valid answer:

```python
try:
    if not path.is_file():
        return None
    with path.open("rb") as handle:
        data = handle.read(max_bytes)
except (OSError, ValueError):
    return None

decoder = codecs.getincrementaldecoder(encoding)(errors="strict")
try:
    text = decoder.decode(data, final=len(data) < max_bytes)    # a cut character waits for its rest
except UnicodeDecodeError:
    return None

return text.replace("\r\n", "\n").replace("\r", "\n")           # the same normalization as read_text
```

</details>

[▲ Back to top](#-table-of-contents)

---

[⬅️ Back to main README](../README.md#-rules--rules-for-files)
