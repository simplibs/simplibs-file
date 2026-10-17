import asyncio
from pathlib import Path
import pytest
from simplibs.actions.testing import assert_action
from simplibs.exception import NotFoundError, StateError, ValidationError
from simplibs.file.actions import FileSize
from simplibs.path.annotations import PathLike


def test_file_size_contract(subtests, tmp_path) -> None:
    """Verify the execution and construction contract of the FileSize action."""
    five = tmp_path / "five.bin"
    five.write_bytes(b"12345")
    empty = tmp_path / "empty.bin"
    empty.write_bytes(b"")
    assert_action(
        subtests,
        FileSize(),
        valid_values=[five, str(five), empty],
        expected_outputs=[5, 5, 0],
        invalid_values=[5, "", tmp_path / "missing", tmp_path],
        expected_exception_type=[ValidationError, ValidationError, NotFoundError, StateError],
        expected_input_type=PathLike,
        expected_output_type=int,
        verbose=False,
    )


def test_file_size_counts_bytes_not_characters(tmp_path) -> None:
    target = tmp_path / "text.txt"
    target.write_bytes("č".encode("utf-8"))
    assert FileSize()(target) == 2


def test_file_size_follows_the_content(tmp_path) -> None:
    target = tmp_path / "grow.bin"
    action = FileSize()
    target.write_bytes(b"1")
    assert action(target) == 1
    target.write_bytes(b"1" * 1000)
    assert action(target) == 1000


def test_file_size_takes_no_configuration() -> None:
    with pytest.raises(TypeError):
        FileSize(unit="kb")


def test_file_size_runs_asynchronously(tmp_path) -> None:
    target = tmp_path / "a.bin"
    target.write_bytes(b"abc")
    assert asyncio.run(FileSize().acall(target)) == 3
