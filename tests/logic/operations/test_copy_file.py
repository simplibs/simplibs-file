import importlib
import os
import stat
from pathlib import Path
import pytest
from simplibs.exception import AccessError, AlreadyExistsError, NotFoundError, ParamError, StateError
from simplibs.file.logic.operations import copy_file

MODULE = importlib.import_module("simplibs.file.logic.operations.copy_file")

_POSIX_ONLY = pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")


def _file(path: Path, data: bytes = b"content") -> Path:
    path.write_bytes(data)
    return path


def _drafts(folder: Path) -> list[Path]:
    return sorted(folder.glob(".*.draft"))


def _symlink_or_skip(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available here")


# ----------------------------------------------------------------------
# The copy
# ----------------------------------------------------------------------

def test_copy_file_copies_the_content_and_keeps_the_source(tmp_path: Path) -> None:
    """The destination is a complete copy; the source is untouched."""
    source = _file(tmp_path / "source.bin", b"\x00\xffdata\r\n")

    copy_file(source, tmp_path / "copy.bin")

    assert (tmp_path / "copy.bin").read_bytes() == b"\x00\xffdata\r\n"
    assert source.read_bytes() == b"\x00\xffdata\r\n"
    assert _drafts(tmp_path) == []


def test_copy_file_returns_the_normalized_destination(tmp_path: Path) -> None:
    """The result is the absolute destination path."""
    source = _file(tmp_path / "source.bin")

    result = copy_file(source, tmp_path / "copy.bin")

    assert isinstance(result, Path)
    assert result == (tmp_path / "copy.bin").resolve()


def test_copy_file_accepts_string_paths(tmp_path: Path) -> None:
    """str paths work like Paths."""
    source = _file(tmp_path / "source.bin")

    copy_file(str(source), str(tmp_path / "copy.bin"))

    assert (tmp_path / "copy.bin").read_bytes() == b"content"


def test_copy_file_creates_missing_folders(tmp_path: Path) -> None:
    """The destination's folder is guaranteed."""
    source = _file(tmp_path / "source.bin")

    copy_file(source, tmp_path / "a" / "b" / "copy.bin")

    assert (tmp_path / "a" / "b" / "copy.bin").read_bytes() == b"content"


def test_copy_file_empty_file(tmp_path: Path) -> None:
    """An empty file is copied as an empty file."""
    source = _file(tmp_path / "source.bin", b"")

    copy_file(source, tmp_path / "copy.bin")

    assert (tmp_path / "copy.bin").read_bytes() == b""


def test_copy_file_large_file(tmp_path: Path) -> None:
    """A multi-megabyte file arrives intact."""
    data = bytes(range(256)) * 12_000
    source = _file(tmp_path / "source.bin", data)

    copy_file(source, tmp_path / "copy.bin")

    assert (tmp_path / "copy.bin").read_bytes() == data


def test_copy_file_relative_paths_resolve_against_the_working_directory(tmp_path: Path, monkeypatch) -> None:
    """Relative paths are normalized."""
    _file(tmp_path / "source.bin")
    monkeypatch.chdir(tmp_path)

    result = copy_file("source.bin", "copy.bin")

    assert result == (tmp_path / "copy.bin").resolve()


def test_copy_file_copies_the_content_behind_a_symlink(tmp_path: Path) -> None:
    """The CONTENT is copied to where the destination path leads."""
    real = _file(tmp_path / "real.bin", b"behind the link")
    link = tmp_path / "link.bin"
    _symlink_or_skip(link, real)

    copy_file(link, tmp_path / "copy.bin")

    assert (tmp_path / "copy.bin").read_bytes() == b"behind the link"
    assert not (tmp_path / "copy.bin").is_symlink()


# ----------------------------------------------------------------------
# Metadata
# ----------------------------------------------------------------------

def test_copy_file_keeps_the_modification_time(tmp_path: Path) -> None:
    """Times of the source arrive on the copy."""
    source = _file(tmp_path / "source.bin")
    os.utime(source, (1_600_000_000, 1_600_000_000))

    copy_file(source, tmp_path / "copy.bin")

    assert int((tmp_path / "copy.bin").stat().st_mtime) == 1_600_000_000


@_POSIX_ONLY
def test_copy_file_keeps_the_permissions(tmp_path: Path) -> None:
    """Permissions of the source arrive on the copy."""
    source = _file(tmp_path / "source.bin")
    os.chmod(source, 0o640)

    copy_file(source, tmp_path / "copy.bin")

    assert stat.S_IMODE((tmp_path / "copy.bin").stat().st_mode) == 0o640


# ----------------------------------------------------------------------
# overwrite
# ----------------------------------------------------------------------

def test_copy_file_default_refuses_an_existing_destination(tmp_path: Path) -> None:
    """overwrite defaults to False — a copy must not destroy a file by accident."""
    source = _file(tmp_path / "source.bin", b"new")
    destination = _file(tmp_path / "copy.bin", b"old")

    with pytest.raises(AlreadyExistsError) as info:
        copy_file(source, destination)

    assert info.value.error_name == "FILE_COPY_DESTINATION_EXISTS"
    assert destination.read_bytes() == b"old"


def test_copy_file_overwrite_replaces_an_existing_destination(tmp_path: Path) -> None:
    """overwrite=True replaces it completely."""
    source = _file(tmp_path / "source.bin", b"new")
    destination = _file(tmp_path / "copy.bin", b"old content that is longer")

    copy_file(source, destination, overwrite=True)

    assert destination.read_bytes() == b"new"
    assert _drafts(tmp_path) == []


def test_copy_file_dangling_symlink_destination_is_refused_without_overwrite(tmp_path: Path) -> None:
    """A dangling link is an existing entry; the copy must not silently remove it."""
    source = _file(tmp_path / "source.bin")
    link = tmp_path / "dangling.bin"
    _symlink_or_skip(link, tmp_path / "gone.bin")

    with pytest.raises(AlreadyExistsError):
        copy_file(source, link)

    assert link.is_symlink()


def test_copy_file_overwrite_false_check_is_a_fail_fast_message_not_a_lock(tmp_path: Path, monkeypatch) -> None:
    """Documented: if the file appears after the check, the swap overwrites it."""
    source = _file(tmp_path / "source.bin", b"new")
    destination = _file(tmp_path / "copy.bin", b"someone was faster")
    monkeypatch.setattr(MODULE, "prepare_destination", lambda *args, **kwargs: None)

    copy_file(source, destination)

    assert destination.read_bytes() == b"new"


# ----------------------------------------------------------------------
# Refusals
# ----------------------------------------------------------------------

def test_copy_file_directory_as_destination_is_a_state_error(tmp_path: Path) -> None:
    """The destination is a FILE path — never a folder to copy into."""
    source = _file(tmp_path / "source.bin")
    folder = tmp_path / "folder"
    folder.mkdir()

    with pytest.raises(StateError) as info:
        copy_file(source, folder)

    assert info.value.error_name == "FILE_COPY_DESTINATION_IS_DIRECTORY"
    assert list(folder.iterdir()) == []


def test_copy_file_onto_itself_is_refused_and_keeps_the_content(tmp_path: Path) -> None:
    """The old implementation would have truncated the file."""
    source = _file(tmp_path / "source.bin", b"precious")

    with pytest.raises(ParamError) as info:
        copy_file(source, source, overwrite=True)

    assert info.value.error_name == "FILE_COPY_SAME_FILE"
    assert source.read_bytes() == b"precious"


def test_copy_file_onto_a_hard_link_of_itself_is_refused(tmp_path: Path) -> None:
    """Another name of the same file is the same file."""
    source = _file(tmp_path / "source.bin", b"precious")
    alias = tmp_path / "alias.bin"
    try:
        os.link(source, alias)
    except (OSError, NotImplementedError):
        pytest.skip("hard links are not available here")

    with pytest.raises(ParamError):
        copy_file(source, alias, overwrite=True)

    assert source.read_bytes() == b"precious"


def test_copy_file_missing_source_raises_not_found(tmp_path: Path) -> None:
    """A missing source is NotFoundError."""
    with pytest.raises(NotFoundError) as info:
        copy_file(tmp_path / "missing.bin", tmp_path / "copy.bin")

    assert info.value.error_name == "FILE_COPY_NOT_FOUND"
    assert not (tmp_path / "copy.bin").exists()


def test_copy_file_directory_as_source_is_a_state_error(tmp_path: Path) -> None:
    """A directory is a card, not a raw OSError."""
    with pytest.raises(StateError) as info:
        copy_file(tmp_path, tmp_path / "copy.bin")

    assert info.value.error_name == "FILE_COPY_NOT_A_FILE"


# ----------------------------------------------------------------------
# OS failures
# ----------------------------------------------------------------------

def test_copy_file_os_failure_is_an_access_error_and_leaves_the_destination_intact(tmp_path: Path, monkeypatch) -> None:
    """The card keeps the original OS exception type and nothing is half-copied."""
    source = _file(tmp_path / "source.bin", b"new")
    destination = _file(tmp_path / "copy.bin", b"old")

    def failing_copy(src, dst, *, sync=False):
        raise PermissionError("denied")

    monkeypatch.setattr(MODULE, "copy_atomically", failing_copy)

    with pytest.raises(AccessError) as info:
        copy_file(source, destination, overwrite=True)

    assert info.value.error_name == "FILE_COPY_FAILED"
    assert isinstance(info.value, PermissionError)
    assert destination.read_bytes() == b"old"


@pytest.mark.parametrize("sync", [False, True])
def test_copy_file_forwards_sync_to_the_atomic_copy(tmp_path: Path, monkeypatch, sync) -> None:
    """The durability flag reaches copy_atomically."""
    received: list[bool] = []
    original_copy = MODULE.copy_atomically

    def recording_copy(src, dst, *, sync=False):
        received.append(sync)
        original_copy(src, dst, sync=sync)

    monkeypatch.setattr(MODULE, "copy_atomically", recording_copy)
    source = _file(tmp_path / "source.bin")

    copy_file(source, tmp_path / "copy.bin", sync=sync)

    assert received == [sync]
