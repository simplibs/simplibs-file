"""Wiring of `@validate_call`: a wrongly typed argument fails BEFORE anything touches the disk.

The single functions are tested for their behaviour in their own files. This file checks
only the seam they share — that every public function really refuses a bad argument with
a `ValidationError`, so a missing or misplaced decorator is caught here.
It imports from the package root on purpose: the test does not depend on the folder layout.
"""
from pathlib import Path
import pytest
from simplibs.exception import ValidationError
from simplibs.file import (
    SafeFileWriter,
    append_bytes,
    append_text,
    backup_file,
    copy_file,
    delete_file,
    file_hash,
    file_size,
    is_text_file,
    iter_lines,
    move_file,
    read_bytes,
    read_json,
    read_lines,
    read_text,
    write_aggregated,
    write_bytes,
    write_json,
    write_lines,
    write_text,
)


def _bad_calls(path: Path) -> dict:
    """One wrongly typed or out-of-range call per public function and per kind of argument."""
    other = path.with_name("other.txt")
    return {
        # read
        "read_bytes: number as path": lambda: read_bytes(5),
        "read_bytes: blank path": lambda: read_bytes(""),
        "read_text: unknown encoding": lambda: read_text(path, encoding="rot13"),
        "read_text: text-only transform as encoding": lambda: read_text(path, encoding="base64"),
        "read_text: unknown errors handler": lambda: read_text(path, errors="nope"),
        "read_text: encode-only errors handler": lambda: read_text(path, errors="xmlcharrefreplace"),
        "read_lines: keep_ends not bool": lambda: read_lines(path, keep_ends="x"),
        "iter_lines: unknown encoding (fails at the call, not at iteration)": lambda: iter_lines(path, encoding="rot13"),
        "read_json: encoding not a string": lambda: read_json(path, encoding=5),
        # write
        "write_bytes: text as data": lambda: write_bytes(path, "text"),
        "write_bytes: number as data": lambda: write_bytes(path, 5),
        "write_bytes: overwrite not bool": lambda: write_bytes(path, b"x", overwrite="x"),
        "append_bytes: text as data": lambda: append_bytes(path, "text"),
        "write_text: bytes as text": lambda: write_text(path, b"x"),
        "write_text: newline outside the allowed modes": lambda: write_text(path, "x", newline="\t"),
        "write_text: unknown encoding": lambda: write_text(path, "x", encoding="rot13"),
        "write_text: use_draft not bool": lambda: write_text(path, "x", use_draft="x"),
        "append_text: sync not bool": lambda: append_text(path, "x", sync="x"),
        "write_lines: number as lines": lambda: write_lines(path, 5),
        "write_lines: non-text items": lambda: write_lines(path, [1, 2]),
        "write_lines: trailing_newline not bool": lambda: write_lines(path, ["a"], trailing_newline="x"),
        "write_aggregated: non-text parts": lambda: write_aggregated(path, [1, 2]),
        "write_aggregated: separator not text": lambda: write_aggregated(path, ["a"], separator=5),
        "write_json: indent of the wrong type": lambda: write_json(path, {}, indent=1.5),
        "write_json: default not callable": lambda: write_json(path, {}, default=5),
        "write_json: allow_nan not bool": lambda: write_json(path, {}, allow_nan="x"),
        # operations
        "copy_file: number as source": lambda: copy_file(5, other),
        "copy_file: blank destination": lambda: copy_file(path, ""),
        "copy_file: overwrite not bool": lambda: copy_file(path, other, overwrite="x"),
        "move_file: overwrite not bool": lambda: move_file(path, other, overwrite="x"),
        "delete_file: force not bool": lambda: delete_file(path, force="x"),
        "delete_file: missing_ok not bool": lambda: delete_file(path, missing_ok="x"),
        "backup_file: suffix not text": lambda: backup_file(path, suffix=5),
        "backup_file: timestamp not bool": lambda: backup_file(path, timestamp="x"),
        # inspect
        "file_size: number as path": lambda: file_size(5),
        "file_hash: zero chunk": lambda: file_hash(path, chunk_size=0),
        "file_hash: negative chunk": lambda: file_hash(path, chunk_size=-1),
        "file_hash: bool as chunk": lambda: file_hash(path, chunk_size=True),
        "file_hash: text as chunk": lambda: file_hash(path, chunk_size="8"),
        "file_hash: unknown algorithm": lambda: file_hash(path, algorithm="nope"),
        "file_hash: variable-length algorithm": lambda: file_hash(path, algorithm="shake_128"),
        "is_text_file: zero sample": lambda: is_text_file(path, sample_size=0),
        "is_text_file: unknown encoding": lambda: is_text_file(path, encoding="rot13"),
        "is_text_file: number as path (validation is on by default)": lambda: is_text_file(5),
        # safe writer
        "SafeFileWriter: number as target": lambda: SafeFileWriter(5),
        "SafeFileWriter: unknown mode": lambda: SafeFileWriter(path, mode="rb"),
        "SafeFileWriter: unknown encoding": lambda: SafeFileWriter(path, encoding="rot13"),
        "SafeFileWriter: sync not bool": lambda: SafeFileWriter(path, sync="x"),
    }


_CASE_NAMES = list(_bad_calls(Path("x.txt")).keys())


@pytest.mark.parametrize("case", _CASE_NAMES)
def test_a_bad_argument_is_refused_before_the_disk_is_touched(tmp_path: Path, case: str) -> None:
    """Every public function raises ValidationError for a bad argument and creates nothing."""
    path = tmp_path / "data.txt"
    call = _bad_calls(path)[case]

    with pytest.raises(ValidationError):
        call()

    assert list(tmp_path.iterdir()) == []


# ----------------------------------------------------------------------
# A control: the same calls with good arguments work, so the table above cannot pass by accident
# ----------------------------------------------------------------------

def test_the_same_calls_with_good_arguments_are_accepted(tmp_path: Path) -> None:
    """Valid values of the arguments tested above are not refused."""
    path = tmp_path / "data.txt"

    write_bytes(path, bytearray(b"abc"))
    assert read_text(path, encoding="utf-8", errors="replace") == "abc"
    assert file_hash(path, algorithm="sha256", chunk_size=1) == file_hash(path)
    assert is_text_file(path, sample_size=1, encoding="utf-8") is True
    assert file_size(path) == 3


# ----------------------------------------------------------------------
# The bare-string trap: `TextCollection` refuses a string where a collection of texts belongs
# ----------------------------------------------------------------------

def test_a_bare_string_is_not_accepted_as_a_collection_of_lines(tmp_path: Path) -> None:
    """`"abc"` is technically a `Collection[str]` (of characters) — writing it as three lines would be a trap.

    A plain `Collection[str]` lets it through, which is why the parameter is a `TextCollection`
    (the same applies to `write_aggregated(parts=...)`).
    """
    path = tmp_path / "lines.txt"

    with pytest.raises(ValidationError):
        write_lines(path, "abc")

    assert not path.exists()


def test_a_bare_string_is_not_accepted_as_a_collection_of_parts(tmp_path: Path) -> None:
    """The same trap for `write_aggregated`: `"abc"` would be joined as `a`, `b`, `c`."""
    path = tmp_path / "parts.txt"

    with pytest.raises(ValidationError):
        write_aggregated(path, "abc")

    assert not path.exists()
