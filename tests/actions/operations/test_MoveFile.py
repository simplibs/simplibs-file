import asyncio
import os
from pathlib import Path
import pytest
from simplibs.actions.testing import assert_action
from simplibs.exception import AlreadyExistsError, NotFoundError, ParamError, StateError, ValidationError
from simplibs.file.actions import MoveFile
from simplibs.path.annotations import PathLike


def test_move_file_contract(subtests, tmp_path) -> None:
    """Verify the execution and construction contract of the MoveFile action."""
    first = tmp_path / "a.txt"
    first.write_text("A")
    second = tmp_path / "b.txt"
    second.write_text("B")
    destination = tmp_path / "out" / "moved.txt"
    assert_action(
        subtests,
        MoveFile(destination=destination, overwrite=True),
        valid_values=[first, str(second)],
        expected_outputs=[destination.resolve()] * 2,
        invalid_values=[5, "", tmp_path / "missing", tmp_path],
        expected_exception_type=[ValidationError, ValidationError, NotFoundError, StateError],
        expected_input_type=PathLike,
        expected_output_type=Path,
        action_class=MoveFile,
        invalid_init_params=[
            ((), {"destination": 5}),
            ((), {"destination": ""}),
            ((), {"destination": None}),
            ((), {"destination": destination, "overwrite": "x"}),
        ],
        verbose=False,
    )


def test_move_file_moves_the_content_and_removes_the_source(tmp_path) -> None:
    source = tmp_path / "a.bin"
    source.write_bytes(b"\x00\xffdata")
    destination = tmp_path / "deep" / "er" / "moved.bin"
    MoveFile(destination=destination)(source)
    assert destination.read_bytes() == b"\x00\xffdata"
    assert not source.exists()


def test_move_file_overwrite_false_refuses_an_existing_destination(tmp_path) -> None:
    source = tmp_path / "a.txt"
    source.write_text("new")
    destination = tmp_path / "moved.txt"
    destination.write_text("old")
    with pytest.raises(AlreadyExistsError):
        MoveFile(destination=destination)(source)
    assert source.read_text() == "new"
    assert destination.read_text() == "old"


def test_move_file_overwrite_true_replaces_the_destination(tmp_path) -> None:
    source = tmp_path / "a.txt"
    source.write_text("new")
    destination = tmp_path / "moved.txt"
    destination.write_text("old")
    MoveFile(destination=destination, overwrite=True)(source)
    assert destination.read_text() == "new"
    assert not source.exists()


def test_move_file_refuses_moving_a_file_onto_itself(tmp_path) -> None:
    source = tmp_path / "a.txt"
    source.write_text("x")
    with pytest.raises(ParamError):
        MoveFile(destination=source, overwrite=True)(source)
    assert source.read_text() == "x"


def test_move_file_refuses_a_directory_at_the_destination(tmp_path) -> None:
    source = tmp_path / "a.txt"
    source.write_text("x")
    folder = tmp_path / "folder"
    folder.mkdir()
    with pytest.raises(StateError):
        MoveFile(destination=folder, overwrite=True)(source)
    assert source.read_text() == "x"


def test_move_file_moves_a_symlink_as_a_link(tmp_path, symlink_or_skip) -> None:
    target = tmp_path / "target.txt"
    target.write_text("x")
    link = tmp_path / "link.txt"
    symlink_or_skip(link, target)
    moved = tmp_path / "moved_link.txt"
    MoveFile(destination=moved)(link)
    assert moved.is_symlink()
    assert not os.path.lexists(link)
    assert target.read_text() == "x"


def test_move_file_has_no_sync_parameter(tmp_path) -> None:
    with pytest.raises(TypeError):
        MoveFile(destination=tmp_path / "x.txt", sync=True)


def test_move_file_runs_asynchronously(tmp_path) -> None:
    source = tmp_path / "a.txt"
    source.write_text("async")
    destination = tmp_path / "moved.txt"
    result = asyncio.run(MoveFile(destination=destination).acall(source))
    assert result == destination.resolve()
    assert destination.read_text() == "async"
    assert not source.exists()


def test_move_file_requires_a_destination() -> None:
    with pytest.raises(TypeError):
        MoveFile()
