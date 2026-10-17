import importlib
import os
import re
import stat
from pathlib import Path
import pytest
from simplibs.exception import AccessError, NotFoundError, ParamError, StateError
from simplibs.file.logic.operations import backup_file

MODULE = importlib.import_module("simplibs.file.logic.operations.backup_file")

_STAMP = "20261013_142530"
_POSIX_ONLY = pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")


@pytest.fixture(autouse=False)
def fixed_clock(monkeypatch):
    """Freeze the timestamp so names are predictable."""
    monkeypatch.setattr(MODULE, "build_timestamp", lambda: _STAMP)


def _file(path: Path, data: bytes = b"content") -> Path:
    path.write_bytes(data)
    return path


def _drafts(folder: Path) -> list[Path]:
    return sorted(folder.glob(".*.draft"))


# ----------------------------------------------------------------------
# Names
# ----------------------------------------------------------------------

def test_backup_file_default_name_has_a_stamp_before_the_extension_and_a_bak_suffix(tmp_path: Path, fixed_clock) -> None:
    """`<stem>_<timestamp><extension>.bak`."""
    source = _file(tmp_path / "report.txt")

    backup = backup_file(source)

    assert backup == (tmp_path / f"report_{_STAMP}.txt.bak").resolve()
    assert backup.read_bytes() == b"content"


def test_backup_file_without_timestamp(tmp_path: Path, fixed_clock) -> None:
    """`<name>.bak`."""
    source = _file(tmp_path / "report.txt")

    assert backup_file(source, timestamp=False) == (tmp_path / "report.txt.bak").resolve()


def test_backup_file_empty_suffix_keeps_only_the_stamp(tmp_path: Path, fixed_clock) -> None:
    """`suffix=""` is allowed."""
    source = _file(tmp_path / "report.txt")

    assert backup_file(source, suffix="") == (tmp_path / f"report_{_STAMP}.txt").resolve()


def test_backup_file_custom_suffix(tmp_path: Path, fixed_clock) -> None:
    """Any well-formed suffix."""
    source = _file(tmp_path / "report.txt")

    assert backup_file(source, suffix=".orig") == (tmp_path / f"report_{_STAMP}.txt.orig").resolve()


def test_backup_file_name_without_extension(tmp_path: Path, fixed_clock) -> None:
    """No extension: the stamp goes at the end of the stem."""
    source = _file(tmp_path / "Makefile")

    assert backup_file(source) == (tmp_path / f"Makefile_{_STAMP}.bak").resolve()


def test_backup_file_dotfile(tmp_path: Path, fixed_clock) -> None:
    """A dotfile has a stem and no suffix."""
    source = _file(tmp_path / ".env")

    assert backup_file(source) == (tmp_path / f".env_{_STAMP}.bak").resolve()


def test_backup_file_double_extension_keeps_only_the_last_one_after_the_stamp(tmp_path: Path, fixed_clock) -> None:
    """The name shape is unchanged from the old version."""
    source = _file(tmp_path / "data.tar.gz")

    assert backup_file(source) == (tmp_path / f"data.tar_{_STAMP}.gz.bak").resolve()


def test_backup_file_real_clock_produces_a_sortable_stamp(tmp_path: Path) -> None:
    """Without patching, the stamp is the real `YYYYMMDD_HHMMSS`."""
    source = _file(tmp_path / "report.txt")

    backup = backup_file(source)

    assert re.fullmatch(r"report_\d{8}_\d{6}\.txt\.bak", backup.name)


# ----------------------------------------------------------------------
# The backup itself
# ----------------------------------------------------------------------

def test_backup_file_copies_the_content_and_keeps_the_source(tmp_path: Path, fixed_clock) -> None:
    """The backup is complete; the source is untouched; no draft remains."""
    source = _file(tmp_path / "report.txt", b"\x00\xffdata\r\n")

    backup = backup_file(source)

    assert backup.read_bytes() == b"\x00\xffdata\r\n"
    assert source.read_bytes() == b"\x00\xffdata\r\n"
    assert _drafts(tmp_path) == []


def test_backup_file_returns_a_normalized_path_next_to_the_source(tmp_path: Path, fixed_clock) -> None:
    """The backup lives in the source's folder."""
    source = _file(tmp_path / "report.txt")

    backup = backup_file(str(source))

    assert isinstance(backup, Path)
    assert backup.is_absolute()
    assert backup.parent == tmp_path.resolve()


def test_backup_file_lives_next_to_the_real_file_not_the_symlink(tmp_path: Path, fixed_clock) -> None:
    """The source is normalized with symlinks resolved."""
    (tmp_path / "real").mkdir()
    (tmp_path / "links").mkdir()
    real = _file(tmp_path / "real" / "report.txt")
    link = tmp_path / "links" / "report.txt"
    try:
        link.symlink_to(real)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available here")

    backup = backup_file(link)

    assert backup.parent == (tmp_path / "real").resolve()
    assert list((tmp_path / "links").iterdir()) == [link]


def test_backup_file_keeps_the_modification_time(tmp_path: Path, fixed_clock) -> None:
    """The backup is a metadata-preserving copy."""
    source = _file(tmp_path / "report.txt")
    os.utime(source, (1_600_000_000, 1_600_000_000))

    backup = backup_file(source)

    assert int(backup.stat().st_mtime) == 1_600_000_000


@_POSIX_ONLY
def test_backup_file_keeps_the_permissions(tmp_path: Path, fixed_clock) -> None:
    """Permissions of the source arrive on the backup."""
    source = _file(tmp_path / "report.txt")
    os.chmod(source, 0o640)

    backup = backup_file(source)

    assert stat.S_IMODE(backup.stat().st_mode) == 0o640


# ----------------------------------------------------------------------
# Never overwrites an older backup
# ----------------------------------------------------------------------

def test_backup_file_two_backups_in_the_same_second_do_not_overwrite_each_other(tmp_path: Path, fixed_clock) -> None:
    """The stamp has a one-second resolution; the second backup gets a free numbered name."""
    source = _file(tmp_path / "report.txt", b"version 1")
    first = backup_file(source)
    source.write_bytes(b"version 2")

    second = backup_file(source)

    assert first != second
    assert first.read_bytes() == b"version 1"
    assert second.read_bytes() == b"version 2"
    assert second.name.startswith(f"report_{_STAMP}")


def test_backup_file_many_backups_in_one_second_all_survive(tmp_path: Path, fixed_clock) -> None:
    """Every backup keeps its own content."""
    source = _file(tmp_path / "report.txt")
    backups = []

    for number in range(5):
        source.write_bytes(f"version {number}".encode("ascii"))
        backups.append(backup_file(source))

    assert len(set(backups)) == 5
    assert [item.read_bytes() for item in backups] == [f"version {n}".encode("ascii") for n in range(5)]


# ----------------------------------------------------------------------
# Refusals
# ----------------------------------------------------------------------

@pytest.mark.parametrize("suffix", ["bak", ".a/b", ".x\\y", "."])
def test_backup_file_malformed_suffix_is_a_param_error(tmp_path: Path, suffix) -> None:
    """`backup_file(suffix="bak")` would build `report.txtbak`."""
    source = _file(tmp_path / "report.txt")

    with pytest.raises(ParamError) as info:
        backup_file(source, suffix=suffix)

    assert info.value.error_name == "FILE_BACKUP_INVALID_SUFFIX"
    assert isinstance(info.value, ValueError)
    assert sorted(item.name for item in tmp_path.iterdir()) == ["report.txt"]


def test_backup_file_suffix_is_checked_before_the_source(tmp_path: Path) -> None:
    """A bad argument is reported even for a file that does not exist."""
    with pytest.raises(ParamError) as info:
        backup_file(tmp_path / "missing.txt", suffix="bak")

    assert info.value.error_name == "FILE_BACKUP_INVALID_SUFFIX"


def test_backup_file_without_stamp_and_suffix_would_be_the_source_itself(tmp_path: Path) -> None:
    """A "backup" equal to the source is a parameter mistake."""
    source = _file(tmp_path / "report.txt", b"precious")

    with pytest.raises(ParamError) as info:
        backup_file(source, timestamp=False, suffix="")

    assert info.value.error_name == "FILE_BACKUP_SAME_FILE"
    assert source.read_bytes() == b"precious"


def test_backup_file_missing_source_raises_not_found(tmp_path: Path) -> None:
    """A missing source is NotFoundError."""
    with pytest.raises(NotFoundError) as info:
        backup_file(tmp_path / "missing.txt")

    assert info.value.error_name == "FILE_BACKUP_NOT_FOUND"


def test_backup_file_directory_source_is_a_state_error(tmp_path: Path) -> None:
    """A directory is a card, not a raw OSError."""
    with pytest.raises(StateError) as info:
        backup_file(tmp_path)

    assert info.value.error_name == "FILE_BACKUP_NOT_A_FILE"


# ----------------------------------------------------------------------
# OS failures
# ----------------------------------------------------------------------

def test_backup_file_os_failure_is_an_access_error_and_leaves_no_backup(tmp_path: Path, monkeypatch, fixed_clock) -> None:
    """A failed copy never leaves something that looks like a real backup."""
    source = _file(tmp_path / "report.txt")

    def failing_copy(src, dst, *, sync=False):
        raise PermissionError("denied")

    monkeypatch.setattr(MODULE, "copy_atomically", failing_copy)

    with pytest.raises(AccessError) as info:
        backup_file(source)

    assert info.value.error_name == "FILE_BACKUP_FAILED"
    assert isinstance(info.value, PermissionError)
    assert sorted(item.name for item in tmp_path.iterdir()) == ["report.txt"]


@pytest.mark.parametrize("sync", [False, True])
def test_backup_file_forwards_sync_to_the_atomic_copy(tmp_path: Path, monkeypatch, fixed_clock, sync) -> None:
    """The durability flag reaches copy_atomically."""
    received: list[bool] = []
    original_copy = MODULE.copy_atomically

    def recording_copy(src, dst, *, sync=False):
        received.append(sync)
        original_copy(src, dst, sync=sync)

    monkeypatch.setattr(MODULE, "copy_atomically", recording_copy)
    source = _file(tmp_path / "report.txt")

    backup_file(source, sync=sync)

    assert received == [sync]
