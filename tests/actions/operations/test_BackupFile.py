import asyncio
import re
from pathlib import Path
import pytest
from simplibs.actions.testing import assert_action
from simplibs.exception import NotFoundError, ParamError, StateError, ValidationError
from simplibs.file.actions import BackupFile
from simplibs.path.annotations import PathLike


def test_backup_file_contract(subtests, tmp_path) -> None:
    """Verify the execution and construction contract of the BackupFile action."""
    first = tmp_path / "a.txt"
    first.write_text("A")
    second = tmp_path / "b.md"
    second.write_text("B")
    assert_action(
        subtests,
        BackupFile(timestamp=False),
        valid_values=[first, str(second)],
        expected_outputs=[(tmp_path / "a.txt.bak").resolve(), (tmp_path / "b.md.bak").resolve()],
        invalid_values=[5, "", tmp_path / "missing", tmp_path],
        expected_exception_type=[ValidationError, ValidationError, NotFoundError, StateError],
        expected_input_type=PathLike,
        expected_output_type=Path,
        action_class=BackupFile,
        invalid_init_params=[
            ((), {"suffix": 5}),
            ((), {"suffix": None}),
            ((), {"timestamp": "x"}),
            ((), {"sync": "x"}),
        ],
        verbose=False,
    )


def test_backup_file_copies_the_content_and_keeps_the_original(tmp_path) -> None:
    source = tmp_path / "report.txt"
    source.write_bytes(b"\x00data\xff")
    backup = BackupFile(timestamp=False)(source)
    assert backup.read_bytes() == b"\x00data\xff"
    assert source.read_bytes() == b"\x00data\xff"
    assert backup != source.resolve()


def test_backup_file_returns_the_backup_not_the_original(tmp_path) -> None:
    source = tmp_path / "report.txt"
    source.write_text("x")
    assert BackupFile(timestamp=False)(source).name == "report.txt.bak"


def test_backup_file_stamps_the_name_by_default(tmp_path) -> None:
    source = tmp_path / "report.txt"
    source.write_text("x")
    backup = BackupFile()(source)
    assert re.fullmatch(r"report_\d{8}_\d{6}\.txt\.bak", backup.name)


def test_backup_file_uses_a_custom_suffix(tmp_path) -> None:
    source = tmp_path / "report.txt"
    source.write_text("x")
    assert BackupFile(suffix=".backup", timestamp=False)(source).name == "report.txt.backup"


def test_backup_file_empty_suffix_is_fine_with_a_timestamp(tmp_path) -> None:
    source = tmp_path / "report.txt"
    source.write_text("x")
    backup = BackupFile(suffix="")(source)
    assert re.fullmatch(r"report_\d{8}_\d{6}\.txt", backup.name)


def test_backup_file_two_backups_never_overwrite_each_other(tmp_path) -> None:
    source = tmp_path / "report.txt"
    action = BackupFile(timestamp=False)
    source.write_text("v1")
    first = action(source)
    source.write_text("v2")
    second = action(source)
    assert first != second
    assert first.read_text() == "v1"
    assert second.read_text() == "v2"


@pytest.mark.parametrize("bad", ["bak", "/x"])
def test_backup_file_rejects_a_malformed_suffix_when_it_runs(tmp_path, bad) -> None:
    source = tmp_path / "report.txt"
    source.write_text("x")
    with pytest.raises(ParamError):
        BackupFile(suffix=bad)(source)


def test_backup_file_refuses_a_backup_equal_to_the_source(tmp_path) -> None:
    source = tmp_path / "report.txt"
    source.write_text("x")
    with pytest.raises(ParamError):
        BackupFile(suffix="", timestamp=False)(source)


def test_backup_file_runs_asynchronously(tmp_path) -> None:
    source = tmp_path / "report.txt"
    source.write_text("x")
    backup = asyncio.run(BackupFile(timestamp=False).acall(source))
    assert backup == (tmp_path / "report.txt.bak").resolve()
    assert backup.read_text() == "x"
