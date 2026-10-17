import asyncio
from pathlib import Path
import pytest
from simplibs.actions import Action
from simplibs.actions.testing import assert_action
from simplibs.exception import AlreadyExistsError, NotFoundError, StateError, ValidationError
from simplibs.file.actions import MoveFile, RenameFile
from simplibs.path.annotations import PathLike


def test_rename_file_contract(subtests, tmp_path) -> None:
    """Verify the execution and construction contract of the RenameFile action."""
    first = tmp_path / "a.txt"
    first.write_text("A")
    second = tmp_path / "b.txt"
    second.write_text("B")
    destination = tmp_path / "out" / "renamed.txt"
    assert_action(
        subtests,
        RenameFile(destination=destination, overwrite=True),
        valid_values=[first, str(second)],
        expected_outputs=[destination.resolve()] * 2,
        invalid_values=[5, "", tmp_path / "missing", tmp_path],
        expected_exception_type=[ValidationError, ValidationError, NotFoundError, StateError],
        expected_input_type=PathLike,
        expected_output_type=Path,
        action_class=RenameFile,
        invalid_init_params=[
            ((), {"destination": 5}),
            ((), {"destination": ""}),
            ((), {"destination": None}),
            ((), {"destination": destination, "overwrite": "x"}),
        ],
        verbose=False,
    )


def test_rename_file_is_its_own_action_class_named_after_itself() -> None:
    assert issubclass(RenameFile, Action)
    assert RenameFile.__name__ == "RenameFile"
    assert RenameFile is not MoveFile


def test_rename_file_renames_the_file(tmp_path) -> None:
    source = tmp_path / "old.txt"
    source.write_text("x")
    destination = tmp_path / "new.txt"
    RenameFile(destination=destination)(source)
    assert destination.read_text() == "x"
    assert not source.exists()


def test_rename_file_overwrite_false_refuses_an_existing_destination(tmp_path) -> None:
    source = tmp_path / "a.txt"
    source.write_text("new")
    destination = tmp_path / "b.txt"
    destination.write_text("old")
    with pytest.raises(AlreadyExistsError):
        RenameFile(destination=destination)(source)
    assert source.read_text() == "new"
    assert destination.read_text() == "old"


def test_rename_file_runs_asynchronously(tmp_path) -> None:
    source = tmp_path / "old.txt"
    source.write_text("async")
    destination = tmp_path / "new.txt"
    result = asyncio.run(RenameFile(destination=destination).acall(source))
    assert result == destination.resolve()
    assert destination.read_text() == "async"


def test_rename_file_requires_a_destination() -> None:
    with pytest.raises(TypeError):
        RenameFile()
