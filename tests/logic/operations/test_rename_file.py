from pathlib import Path
from simplibs.file.logic.operations import move_file, rename_file


def test_rename_file_is_the_very_same_function_as_move_file() -> None:
    """An alias cannot drift — same parameters, same behaviour, nothing to keep in sync."""
    assert rename_file is move_file


def test_rename_file_keeps_the_name_of_the_real_function() -> None:
    """Error cards and tracebacks name the real function."""
    assert rename_file.__name__ == "move_file"


def test_rename_file_still_renames(tmp_path: Path) -> None:
    """Code written against the old name keeps working."""
    source = tmp_path / "old.txt"
    source.write_bytes(b"data")

    result = rename_file(source, tmp_path / "new.txt")

    assert result == tmp_path.resolve() / "new.txt"
    assert (tmp_path / "new.txt").read_bytes() == b"data"
    assert not source.exists()
