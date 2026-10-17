import asyncio
from pathlib import Path
import pytest
from simplibs.actions.testing import assert_action
from simplibs.exception import NotFoundError, StateError, ValidationError
from simplibs.file.actions import ReadBytes
from simplibs.path.annotations import PathLike


def test_read_bytes_contract(subtests, tmp_path) -> None:
    """Verify the execution and construction contract of the ReadBytes action."""
    raw = tmp_path / "raw.bin"
    raw.write_bytes(b"\x00\xff\r\n\x10")
    empty = tmp_path / "empty.bin"
    empty.write_bytes(b"")
    assert_action(
        subtests,
        ReadBytes(),
        valid_values=[raw, str(raw), empty],
        expected_outputs=[b"\x00\xff\r\n\x10", b"\x00\xff\r\n\x10", b""],
        invalid_values=[5, "", tmp_path / "missing", tmp_path],
        expected_exception_type=[ValidationError, ValidationError, NotFoundError, StateError],
        expected_input_type=PathLike,
        expected_output_type=bytes,
        verbose=False,
    )


def test_read_bytes_does_not_translate_line_endings(tmp_path) -> None:
    target = tmp_path / "crlf.txt"
    target.write_bytes(b"a\r\nb\rc\nd")
    assert ReadBytes()(target) == b"a\r\nb\rc\nd"


def test_read_bytes_takes_no_configuration() -> None:
    with pytest.raises(TypeError):
        ReadBytes(encoding="utf-8")


def test_read_bytes_runs_asynchronously(tmp_path) -> None:
    target = tmp_path / "a.bin"
    target.write_bytes(b"abc")
    assert asyncio.run(ReadBytes().acall(target)) == b"abc"
