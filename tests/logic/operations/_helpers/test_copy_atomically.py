import importlib
import os
import shutil
import stat
from pathlib import Path
from types import SimpleNamespace
import pytest
from simplibs.file.logic.operations._helpers import copy_atomically

MODULE = importlib.import_module("simplibs.file.logic.operations._helpers.copy_atomically")

_POSIX_ONLY = pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")


def _drafts(folder: Path) -> list[Path]:
    return sorted(folder.glob(".*.draft"))


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


# ----------------------------------------------------------------------
# The copy
# ----------------------------------------------------------------------

def test_copy_atomically_copies_the_exact_content(tmp_path: Path) -> None:
    """Every byte arrives, the source stays."""
    source = tmp_path / "source.bin"
    destination = tmp_path / "copy.bin"
    source.write_bytes(b"\x00\xffdata\r\nmore")

    copy_atomically(source, destination)

    assert destination.read_bytes() == b"\x00\xffdata\r\nmore"
    assert source.read_bytes() == b"\x00\xffdata\r\nmore"
    assert _drafts(tmp_path) == []


def test_copy_atomically_returns_none(tmp_path: Path) -> None:
    """The copy has no result."""
    source = tmp_path / "source.bin"
    source.write_bytes(b"x")

    assert copy_atomically(source, tmp_path / "copy.bin") is None


def test_copy_atomically_replaces_an_existing_destination(tmp_path: Path) -> None:
    """The destination becomes the complete copy."""
    source = tmp_path / "source.bin"
    destination = tmp_path / "copy.bin"
    source.write_bytes(b"new")
    destination.write_bytes(b"old content that is longer")

    copy_atomically(source, destination)

    assert destination.read_bytes() == b"new"


def test_copy_atomically_empty_file(tmp_path: Path) -> None:
    """An empty file is copied as an empty file."""
    source = tmp_path / "source.bin"
    source.write_bytes(b"")

    copy_atomically(source, tmp_path / "copy.bin")

    assert (tmp_path / "copy.bin").read_bytes() == b""


def test_copy_atomically_large_file(tmp_path: Path) -> None:
    """A multi-megabyte file arrives intact."""
    data = bytes(range(256)) * 12_000
    source = tmp_path / "source.bin"
    source.write_bytes(data)

    copy_atomically(source, tmp_path / "copy.bin")

    assert (tmp_path / "copy.bin").read_bytes() == data


def test_copy_atomically_copies_the_content_behind_a_symlink(tmp_path: Path) -> None:
    """A link as the source gives a regular file with the link's content."""
    real = tmp_path / "real.bin"
    real.write_bytes(b"content")
    link = tmp_path / "link.bin"
    try:
        link.symlink_to(real)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available here")

    copy_atomically(link, tmp_path / "copy.bin")

    assert (tmp_path / "copy.bin").read_bytes() == b"content"
    assert not (tmp_path / "copy.bin").is_symlink()


# ----------------------------------------------------------------------
# Metadata
# ----------------------------------------------------------------------

def test_copy_atomically_keeps_the_modification_time(tmp_path: Path) -> None:
    """`copystat`, like `copy2`."""
    source = tmp_path / "source.bin"
    source.write_bytes(b"x")
    os.utime(source, (1_600_000_000, 1_600_000_000))

    copy_atomically(source, tmp_path / "copy.bin")

    assert int((tmp_path / "copy.bin").stat().st_mtime) == 1_600_000_000


@_POSIX_ONLY
def test_copy_atomically_new_destination_gets_the_mode_of_the_source(tmp_path: Path) -> None:
    """Permissions of the source arrive on the copy."""
    source = tmp_path / "source.bin"
    source.write_bytes(b"x")
    os.chmod(source, 0o640)

    copy_atomically(source, tmp_path / "copy.bin")

    assert _mode(tmp_path / "copy.bin") == 0o640


@_POSIX_ONLY
def test_copy_atomically_replaced_destination_takes_the_mode_of_the_source(tmp_path: Path) -> None:
    """keep_mode=False: a copy carries the permissions of its SOURCE, not of the file it replaces."""
    source = tmp_path / "source.bin"
    destination = tmp_path / "copy.bin"
    source.write_bytes(b"x")
    destination.write_bytes(b"old")
    os.chmod(source, 0o640)
    os.chmod(destination, 0o600)

    copy_atomically(source, destination)

    assert _mode(destination) == 0o640


# ----------------------------------------------------------------------
# Failures leave nothing behind
# ----------------------------------------------------------------------

@pytest.mark.parametrize("error", [OSError("disk full"), KeyboardInterrupt()], ids=["OSError", "KeyboardInterrupt"])
def test_copy_atomically_interrupted_copy_leaves_no_draft_and_the_destination_intact(
    tmp_path: Path, monkeypatch, error,
) -> None:
    """A failure while copying the data: the old destination survives, the draft is removed."""
    source = tmp_path / "source.bin"
    destination = tmp_path / "copy.bin"
    source.write_bytes(b"new")
    destination.write_bytes(b"old")

    def failing_copyfile(src, dst):
        raise error

    monkeypatch.setattr(MODULE, "shutil", SimpleNamespace(copyfile=failing_copyfile, copystat=shutil.copystat))

    with pytest.raises(type(error)):
        copy_atomically(source, destination)

    assert destination.read_bytes() == b"old"
    assert _drafts(tmp_path) == []


def test_copy_atomically_interrupted_copy_does_not_create_the_destination(tmp_path: Path, monkeypatch) -> None:
    """No truncated file that looks complete."""
    source = tmp_path / "source.bin"
    source.write_bytes(b"new")

    def failing_copyfile(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(MODULE, "shutil", SimpleNamespace(copyfile=failing_copyfile, copystat=shutil.copystat))

    with pytest.raises(OSError):
        copy_atomically(source, tmp_path / "copy.bin")

    assert not (tmp_path / "copy.bin").exists()
    assert _drafts(tmp_path) == []


def test_copy_atomically_failed_commit_removes_the_draft(tmp_path: Path, monkeypatch) -> None:
    """The swap itself fails: the destination is untouched and no draft remains."""
    source = tmp_path / "source.bin"
    destination = tmp_path / "copy.bin"
    source.write_bytes(b"new")
    destination.write_bytes(b"old")

    def refusing_commit(draft_path, target_path, **kwargs):
        raise PermissionError("locked")

    monkeypatch.setattr(MODULE, "commit_draft", refusing_commit)

    with pytest.raises(PermissionError):
        copy_atomically(source, destination)

    assert destination.read_bytes() == b"old"
    assert _drafts(tmp_path) == []


def test_copy_atomically_missing_source_fails_cleanly(tmp_path: Path) -> None:
    """Nothing is created for a source that does not exist."""
    with pytest.raises(FileNotFoundError):
        copy_atomically(tmp_path / "missing.bin", tmp_path / "copy.bin")

    assert not (tmp_path / "copy.bin").exists()
    assert _drafts(tmp_path) == []


def test_copy_atomically_missing_destination_folder_fails_cleanly(tmp_path: Path) -> None:
    """The destination's folder must already exist — nothing is created."""
    source = tmp_path / "source.bin"
    source.write_bytes(b"x")

    with pytest.raises(OSError):
        copy_atomically(source, tmp_path / "nofolder" / "copy.bin")

    assert not (tmp_path / "nofolder").exists()


# ----------------------------------------------------------------------
# Forwarded options
# ----------------------------------------------------------------------

@pytest.mark.parametrize("sync", [False, True])
def test_copy_atomically_commits_with_keep_mode_false_and_forwards_sync(tmp_path: Path, monkeypatch, sync) -> None:
    """The draft is swapped in without overwriting the copied permissions."""
    received: list[dict] = []
    original_commit = MODULE.commit_draft

    def recording_commit(draft_path, target_path, **kwargs):
        received.append(kwargs)
        original_commit(draft_path, target_path, **kwargs)

    monkeypatch.setattr(MODULE, "commit_draft", recording_commit)
    source = tmp_path / "source.bin"
    source.write_bytes(b"x")

    copy_atomically(source, tmp_path / "copy.bin", sync=sync)

    assert received == [{"keep_mode": False, "sync": sync}]
