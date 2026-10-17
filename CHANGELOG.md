# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [0.1.0] - 2026-10-17

### ✨ Added

#### Read — a file in, its content out

* `read_bytes(path)` — the raw content; the core every other reader is built on
* `read_text(path, *, encoding="utf-8-sig", errors="strict")` — the whole
  text, BOM-tolerant, line endings normalized to `"\n"`
* `read_lines(path, *, encoding, errors, keep_ends=False)` — a list of lines;
  only `\n`, `\r\n` and `\r` end a line, and with `keep_ends=True` every line
  keeps its original ending
* `iter_lines(...)` — the lazy counterpart of `read_lines`; the path is checked
  when called, the content while iterating
* `read_json(path, *, encoding, errors)` — reads and parses JSON; a syntax
  error is a card with the line and column
* Bytes are decoded in memory, so an undecodable file is a `ConversionError`
  card instead of a bare `UnicodeDecodeError`

#### Write — content in, a file out

* `write_bytes(path, data, *, overwrite=True, use_draft=True, sync=False)` —
  the first core writer
* `append_bytes(path, data, *, use_draft=False, sync=False)` — the second core
  writer; creates the file when it is missing
* `write_text`, `append_text` — encode in memory first, so an unencodable
  character fails before the disk is touched; deterministic defaults (`utf-8`
  without BOM, `"\n"` line endings); a BOM is never appended into the middle
  of a file
* `write_lines`, `write_aggregated`, `write_json` — one item per line, joined
  fragments with a separator, and a serialized JSON document; all build the
  text and hand it to `write_text`
* The target's folder is created when missing; a directory at the target is a
  `StateError`; `overwrite=False` raises `AlreadyExistsError`

#### Operations — work with the file itself

* `copy_file(source, destination, *, overwrite=False, sync=False)` — atomic
  copy keeping permissions and times; the destination is always a file path
* `move_file(source, destination, *, overwrite=False)` — moves or renames across
  folders **and devices**; a symlink is moved as a link; a case-only rename is
  allowed on Windows
* `rename_file` — the old name of `move_file` (the same function)
* `delete_file(path, *, missing_ok=False, force=False)` — deletes a file or a
  symlink, never the link's target; `force` clears the read-only flag
* `backup_file(path, *, suffix=".bak", timestamp=True, sync=False)` — an atomic
  backup next to the file that never overwrites an older one

#### Inspect — ask a file about itself

* `file_size(path)` — the size in bytes from one `stat`
* `file_hash(path, *, algorithm="sha256", chunk_size=1_048_576)` — the hex digest
  of the content, read in chunks; `md5` and `sha1` are declared non-security so
  they also work on FIPS-restricted systems
* `is_text_file(path, *, sample_size=8192, encoding="utf-8")` — a predicate that
  never raises for disk problems

#### Safe writing

* `SafeFileWriter` — a context manager for crash-safe writing by draft and swap:
  the target is replaced in one atomic step only when the block ends without an
  exception; a failed block, a failed close and a failed swap all leave the
  original untouched and remove the draft; permissions of the replaced file are
  kept; `sync=True` makes the result survive a power loss
* `IGNORE_DRAFTS` — a scanner `ignore_names` pattern for leftover drafts
  (opt-in: `DEFAULT_IGNORE_NAMES | IGNORE_DRAFTS`)

#### Rules — `simplibs.file.rules`

* `IsTextFile` — a readable file whose beginning looks like text
* `SizeIs(rule)` and `ContentIs(rule, *, encoding, max_bytes)` — lenses that point
  any numeric or string rule of `simplibs-rules` at a file's size or at the
  beginning of its text; the failure card is the wrapped rule's own, labelled
  `source.size` / `source.content`
* Every rule returns a strict `bool` without raising, describes itself
  (`describe()`), composes with `&`, `|` and `~`, and combines with the path
  rules of `simplibs-path`

#### Actions — `simplibs.file.actions`

* Read: `ReadBytes`, `ReadText`, `ReadLines`, `ReadJson`
* Write, the content flows: `WriteBytes`, `AppendBytes`, `WriteText`,
  `AppendText`, `WriteLines`, `WriteAggregated`, `WriteJson`
* Write, the path flows: `WriteBytesTo`, `AppendBytesTo`, `WriteTextTo`,
  `AppendTextTo`, `WriteLinesTo`, `WriteAggregatedTo`, `WriteJsonTo`
* Operations: `CopyFile`, `CopyFileFrom`, `MoveFile`, `RenameFile`, `DeleteFile`,
  `BackupFile`
* Inspect: `FileSize`, `FileHash`
* Chainable with `>>`, `&` and `|`, awaitable through `acall`, and usable directly
  behind a `Rule` (`IsTextFile() >> ReadText()`)

#### Annotations

* `EncodingName` — a text encoding Python can both encode and decode with
  (rejects `"rot13"`, `"base64"` and unknown names)
* `EncodingErrors` — the error handlers that work in both directions
* `NewlineMode` — `"\n"`, `"\r\n"`, `"\r"` or `None` for the platform's own
* `ByteCount` — a positive number of bytes (rejects zero, negatives and `bool`)
* `HashAlgorithm` — the twelve fixed-length algorithms of `hashlib`
* `WriterMode` — the four open modes `SafeFileWriter` supports

#### Package Layout

* `simplibs.file` exports the functions, `SafeFileWriter`, `IGNORE_DRAFTS` and the
  six annotations directly; `rules` and `actions` are domain packages with their
  own `__all__`
* `PathLike` is reused from `simplibs.path`

#### Documentation

* Main `README.md` with quick start, package structure and platform notes
* Detailed reference for each part: read, write, operations, inspect and
  safe writer under `docs/logic/`, plus rules, actions and annotations, each
  function and class documented with parameters, return values, raised errors,
  examples and the logic behind it

#### Quality Assurance

* Test suite mirroring the source layout, covering functions, rules, actions,
  helpers and error diagnostics
* Contract tests for every rule (`assert_rule_contract`) and action
  (`assert_action`)
* Platform-aware tests for symlinks and permissions, skipped where the platform
  or privileges do not allow them

#### Dependencies

* `simplibs-path` — the paths themselves; `PathLike`, normalization and the
  public `simplibs.path.tools` toolkit
* `simplibs-exception` — structured exceptions for every diagnostic
* `simplibs-validate` — `@validate_call` on every public function and the
  validated annotation types
* `simplibs-rules` — the `Rule` engine behind `simplibs.file.rules`
* `simplibs-actions` — the `Action` abstraction behind `simplibs.file.actions`

---

## Legend

* 🔄 **Changed** — modifications to existing functionality
* ✨ **Added** — new features and components
* 🐛 **Fixed** — bug fixes
* 📋 **Improved** — enhancements to existing features
* ⚠️ **Deprecated** — deprecated functionality (not used yet in this
  project)
* 🗑️ **Removed** — removed functionality (not used yet in this project)
