import asyncio
import os
from pathlib import Path
import pytest
from simplibs.actions.testing import assert_action
from simplibs.exception import NotFoundError, StateError, ValidationError
from simplibs.file.actions import DeleteFile
from simplibs.path.annotations import PathLike


def test_delete_file_contract(subtests, tmp_path) -> None:
    """Verify the execution and construction contract of the DeleteFile action."""
    first = tmp_path / "a.txt"
    first.write_text("A")
    second = tmp_path / "b.txt"
    second.write_text("B")
    assert_action(
        subtests,
        DeleteFile(),
        valid_values=[first, str(second)],
        expected_outputs=[first.resolve(), second.resolve()],
        invalid_values=[5, "", tmp_path / "missing", tmp_path],
        expected_exception_type=[ValidationError, ValidationError, NotFoundError, StateError],
        expected_input_type=PathLike,
        expected_output_type=Path,
        action_class=DeleteFile,
        invalid_init_params=[
            ((), {"missing_ok": "x"}),
            ((), {"force": "x"}),
        ],
        verbose=False,
    )


def test_delete_file_really_deletes_the_file(tmp_path) -> None:
    target = tmp_path / "a.txt"
    target.write_text("x")
    DeleteFile()(target)
    assert not target.exists()


def test_delete_file_missing_ok_accepts_a_missing_path(tmp_path) -> None:
    missing = tmp_path / "missing.txt"
    assert DeleteFile(missing_ok=True)(missing) == missing.resolve()


def test_delete_file_does_not_touch_a_directory(tmp_path) -> None:
    folder = tmp_path / "folder"
    folder.mkdir()
    with pytest.raises(StateError):
        DeleteFile(missing_ok=True)(folder)
    assert folder.is_dir()


def test_delete_file_deletes_a_symlink_but_not_its_target(tmp_path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("x")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("Creating symlinks is not permitted here.")
    result = DeleteFile()(link)
    assert result == tmp_path.resolve() / "link.txt"
    assert not os.path.lexists(link)
    assert target.read_text() == "x"


def test_delete_file_can_delete_a_dangling_symlink(tmp_path) -> None:
    link = tmp_path / "dangling.txt"
    try:
        link.symlink_to(tmp_path / "nowhere.txt")
    except (OSError, NotImplementedError):
        pytest.skip("Creating symlinks is not permitted here.")
    DeleteFile()(link)
    assert not os.path.lexists(link)


def test_delete_file_runs_asynchronously(tmp_path) -> None:
    target = tmp_path / "async.txt"
    target.write_text("x")
    result = asyncio.run(DeleteFile().acall(target))
    assert result == target.resolve()
    assert not target.exists()
