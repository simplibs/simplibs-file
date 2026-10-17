"""Locked and read-only files — what Windows does to a file that is in use or marked read-only.

Other systems let you replace or delete such a file, so these tests run on Windows only. Every
failure must come out as a card, leave the original untouched and leave no draft behind.
"""
import os
import stat
import threading
from pathlib import Path
import pytest
from simplibs.exception import AccessError
from simplibs.file import copy_file, delete_file, file_hash, move_file, read_bytes, write_bytes

pytestmark = pytest.mark.windows_only("locked and read-only files")


def _file(path: Path, data: bytes = b"precious") -> Path:
    path.write_bytes(data)
    return path


def _drafts(folder: Path) -> list[Path]:
    return sorted(folder.glob(".*.draft"))


def _read_only(path: Path) -> None:
    os.chmod(path, stat.S_IREAD)


def _writable(path: Path) -> None:
    os.chmod(path, stat.S_IREAD | stat.S_IWRITE)


# ----------------------------------------------------------------------
# A locked file cannot be read
# ----------------------------------------------------------------------

def test_read_bytes_of_a_locked_file_is_an_access_error(tmp_path: Path, lock_file) -> None:
    """The OS refuses the read; the card says so instead of a bare PermissionError."""
    source = _file(tmp_path / "a.bin")

    with lock_file(source):
        with pytest.raises(AccessError) as info:
            read_bytes(source)

    assert info.value.error_name == "FILE_READ_FAILED"
    assert isinstance(info.value, PermissionError)
    assert read_bytes(source) == b"precious"


def test_file_hash_of_a_locked_file_is_an_access_error(tmp_path: Path, lock_file) -> None:
    """Hashing needs the content, so a lock is a card as well."""
    source = _file(tmp_path / "a.bin")

    with lock_file(source):
        with pytest.raises(AccessError) as info:
            file_hash(source)

    assert info.value.error_name == "FILE_HASH_FAILED"


# ----------------------------------------------------------------------
# A locked target cannot be written
# ----------------------------------------------------------------------

def test_write_bytes_to_a_locked_target_keeps_the_original_and_leaves_no_draft(tmp_path: Path, lock_file) -> None:
    """The swap is retried, then fails; nothing is half written and the draft is removed."""
    target = _file(tmp_path / "a.bin")

    with lock_file(target):
        with pytest.raises(AccessError) as info:
            write_bytes(target, b"new")

    assert info.value.error_name == "SAFE_WRITER_COMMIT_FAILED"
    assert target.read_bytes() == b"precious"
    assert _drafts(tmp_path) == []

    write_bytes(target, b"new")                     # once the lock is gone, the very same call works
    assert target.read_bytes() == b"new"


def test_write_bytes_in_place_to_a_locked_target_is_an_access_error(tmp_path: Path, lock_file) -> None:
    """Without a draft the file cannot even be opened; it is not truncated."""
    target = _file(tmp_path / "a.bin")

    with lock_file(target):
        with pytest.raises(AccessError) as info:
            write_bytes(target, b"new", use_draft=False)

    assert info.value.error_name == "FILE_WRITE_FAILED"
    assert target.read_bytes() == b"precious"


def test_write_bytes_waits_out_a_lock_that_is_released_in_time(tmp_path: Path, lock_file) -> None:
    """A short lock (antivirus, indexer) is exactly what the retry in the swap is for."""
    target = _file(tmp_path / "a.bin")
    lock = lock_file(target)
    lock.__enter__()
    releaser = threading.Timer(0.05, lambda: lock.__exit__(None, None, None))
    releaser.start()
    try:
        write_bytes(target, b"new")
    finally:
        releaser.join()

    assert target.read_bytes() == b"new"
    assert _drafts(tmp_path) == []


# ----------------------------------------------------------------------
# A locked file cannot be deleted, moved or copied over
# ----------------------------------------------------------------------

@pytest.mark.parametrize("force", [False, True])
def test_delete_file_of_a_locked_file_is_an_access_error(tmp_path: Path, lock_file, force) -> None:
    """`force` clears a read-only flag — it cannot open a lock."""
    target = _file(tmp_path / "a.bin")

    with lock_file(target):
        with pytest.raises(AccessError) as info:
            delete_file(target, force=force)

    assert info.value.error_name == "FILE_DELETE_FAILED"
    assert target.read_bytes() == b"precious"

    delete_file(target)
    assert not target.exists()


def test_move_file_of_a_locked_source_keeps_the_source(tmp_path: Path, lock_file) -> None:
    """The rename is retried, then reported; the file stays where it was."""
    source = _file(tmp_path / "a.bin")

    with lock_file(source):
        with pytest.raises(AccessError) as info:
            move_file(source, tmp_path / "b.bin")

    assert info.value.error_name == "FILE_MOVE_FAILED"
    assert source.read_bytes() == b"precious"
    assert not (tmp_path / "b.bin").exists()


def test_copy_file_of_a_locked_source_leaves_nothing_behind(tmp_path: Path, lock_file) -> None:
    """The source cannot be read: no destination, no draft."""
    source = _file(tmp_path / "a.bin")

    with lock_file(source):
        with pytest.raises(AccessError) as info:
            copy_file(source, tmp_path / "b.bin")

    assert info.value.error_name == "FILE_COPY_FAILED"
    assert not (tmp_path / "b.bin").exists()
    assert _drafts(tmp_path) == []


def test_copy_file_over_a_locked_destination_keeps_the_destination(tmp_path: Path, lock_file) -> None:
    """The finished copy cannot take its place; the old file is intact and the draft is removed."""
    source = _file(tmp_path / "a.bin", b"new")
    destination = _file(tmp_path / "b.bin")

    with lock_file(destination):
        with pytest.raises(AccessError) as info:
            copy_file(source, destination, overwrite=True)

    assert info.value.error_name == "FILE_COPY_FAILED"
    assert destination.read_bytes() == b"precious"
    assert _drafts(tmp_path) == []


# ----------------------------------------------------------------------
# A read-only target cannot be replaced
# ----------------------------------------------------------------------

def test_write_bytes_over_a_read_only_file_keeps_it_and_leaves_no_draft(tmp_path: Path) -> None:
    """Windows refuses to replace a read-only file; the card is raised and the draft removed."""
    target = _file(tmp_path / "a.bin")
    _read_only(target)
    try:
        with pytest.raises(AccessError) as info:
            write_bytes(target, b"new")
    finally:
        _writable(target)

    assert info.value.error_name == "SAFE_WRITER_COMMIT_FAILED"
    assert target.read_bytes() == b"precious"
    assert _drafts(tmp_path) == []


def test_copy_file_over_a_read_only_destination_keeps_it(tmp_path: Path) -> None:
    """The same for a copy with `overwrite=True`."""
    source = _file(tmp_path / "a.bin", b"new")
    destination = _file(tmp_path / "b.bin")
    _read_only(destination)
    try:
        with pytest.raises(AccessError) as info:
            copy_file(source, destination, overwrite=True)
    finally:
        _writable(destination)

    assert info.value.error_name == "FILE_COPY_FAILED"
    assert destination.read_bytes() == b"precious"
    assert _drafts(tmp_path) == []
