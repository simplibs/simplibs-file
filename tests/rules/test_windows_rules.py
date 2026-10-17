"""Rules and a locked file — the Windows counterpart of the "unreadable file" tests.

On POSIX a file is made unreadable with `chmod 000`; Windows has no such permission bit, so the
same situation is a file held by another program. A rule must answer `False` / `None` and never raise.
"""
from pathlib import Path
import pytest
from simplibs.file.rules import IsTextFile
from simplibs.file.rules._helpers import read_file_head

pytestmark = pytest.mark.windows_only("a locked file stands in for an unreadable one")


def test_read_file_head_is_none_for_a_locked_file(tmp_path: Path, lock_file) -> None:
    target = tmp_path / "a.txt"
    target.write_bytes(b"x")

    with lock_file(target):
        assert read_file_head(target, max_bytes=1000, encoding="utf-8") is None

    assert read_file_head(target, max_bytes=1000, encoding="utf-8") == "x"


def test_is_text_file_a_locked_file_is_not_a_text_file(tmp_path: Path, lock_file) -> None:
    target = tmp_path / "a.txt"
    target.write_text("x")

    with lock_file(target):
        assert IsTextFile().is_valid(target) is False

    assert IsTextFile().is_valid(target) is True
