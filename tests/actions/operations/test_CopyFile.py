import asyncio
from pathlib import Path
import pytest
from simplibs.actions.testing import assert_action
from simplibs.exception import AlreadyExistsError, NotFoundError, ParamError, StateError, ValidationError
from simplibs.file.actions import CopyFile
from simplibs.path.annotations import PathLike


def test_copy_file_contract(subtests, tmp_path) -> None:
    """Verify the execution and construction contract of the CopyFile action."""
    source = tmp_path / "a.txt"
    source.write_text("A")
    destination = tmp_path / "out" / "copy.txt"
    assert_action(
        subtests,
        CopyFile(destination=destination, overwrite=True),
        valid_values=[source, str(source)],
        expected_outputs=[destination.resolve()] * 2,
        invalid_values=[5, "", tmp_path / "missing", tmp_path],
        expected_exception_type=[ValidationError, ValidationError, NotFoundError, StateError],
        expected_input_type=PathLike,
        expected_output_type=Path,
        action_class=CopyFile,
        invalid_init_params=[
            ((), {"destination": 5}),
            ((), {"destination": ""}),
            ((), {"destination": None}),
            ((), {"destination": destination, "overwrite": "x"}),
            ((), {"destination": destination, "sync": "x"}),
        ],
        verbose=False,
    )


def test_copy_file_copies_the_content_and_keeps_the_source(tmp_path) -> None:
    source = tmp_path / "a.bin"
    source.write_bytes(b"\x00\xffdata")
    destination = tmp_path / "deep" / "er" / "copy.bin"
    CopyFile(destination=destination)(source)
    assert destination.read_bytes() == b"\x00\xffdata"
    assert source.read_bytes() == b"\x00\xffdata"


def test_copy_file_overwrite_false_refuses_an_existing_destination(tmp_path) -> None:
    source = tmp_path / "a.txt"
    source.write_text("new")
    destination = tmp_path / "copy.txt"
    destination.write_text("old")
    with pytest.raises(AlreadyExistsError):
        CopyFile(destination=destination)(source)
    assert destination.read_text() == "old"


def test_copy_file_overwrite_true_replaces_the_destination(tmp_path) -> None:
    source = tmp_path / "a.txt"
    source.write_text("new")
    destination = tmp_path / "copy.txt"
    destination.write_text("old")
    CopyFile(destination=destination, overwrite=True)(source)
    assert destination.read_text() == "new"


def test_copy_file_refuses_copying_a_file_onto_itself(tmp_path) -> None:
    source = tmp_path / "a.txt"
    source.write_text("x")
    with pytest.raises(ParamError):
        CopyFile(destination=source, overwrite=True)(source)
    assert source.read_text() == "x"


def test_copy_file_destination_is_a_file_path_never_a_folder(tmp_path) -> None:
    source = tmp_path / "a.txt"
    source.write_text("x")
    folder = tmp_path / "folder"
    folder.mkdir()
    with pytest.raises(StateError):
        CopyFile(destination=folder, overwrite=True)(source)


def test_copy_file_runs_asynchronously(tmp_path) -> None:
    source = tmp_path / "a.txt"
    source.write_text("async")
    destination = tmp_path / "copy.txt"
    result = asyncio.run(CopyFile(destination=destination).acall(source))
    assert result == destination.resolve()
    assert destination.read_text() == "async"


def test_copy_file_requires_a_destination() -> None:
    with pytest.raises(TypeError):
        CopyFile()
