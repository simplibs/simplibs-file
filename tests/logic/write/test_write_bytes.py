import importlib
import os
from pathlib import Path
from types import SimpleNamespace
import pytest
from simplibs.exception import AccessError, AlreadyExistsError, StateError, ValidationError
from simplibs.file.logic.write import write_bytes

MODULE = importlib.import_module("simplibs.file.logic.write.write_bytes")


def _drafts(folder: Path) -> list[Path]:
    return sorted(folder.glob(".*.draft"))


# ----------------------------------------------------------------------
# Writing
# ----------------------------------------------------------------------

@pytest.mark.parametrize("use_draft", [True, False])
def test_write_bytes_writes_a_new_file(tmp_path: Path, use_draft) -> None:
    """Both the draft and the direct path produce the same file."""
    target = tmp_path / "out.bin"

    write_bytes(target, b"\x00\xffdata", use_draft=use_draft)

    assert target.read_bytes() == b"\x00\xffdata"
    assert _drafts(tmp_path) == []


@pytest.mark.parametrize("use_draft", [True, False])
def test_write_bytes_replaces_an_existing_file(tmp_path: Path, use_draft) -> None:
    """overwrite defaults to True."""
    target = tmp_path / "out.bin"
    target.write_bytes(b"old content that is longer")

    write_bytes(target, b"new", use_draft=use_draft)

    assert target.read_bytes() == b"new"


@pytest.mark.parametrize("use_draft", [True, False])
def test_write_bytes_empty_data_creates_an_empty_file(tmp_path: Path, use_draft) -> None:
    """An empty write is still a write."""
    target = tmp_path / "empty.bin"

    write_bytes(target, b"", use_draft=use_draft)

    assert target.read_bytes() == b""


def test_write_bytes_returns_the_normalized_path(tmp_path: Path) -> None:
    """The result is the absolute, resolved target."""
    result = write_bytes(tmp_path / "out.bin", b"x")

    assert isinstance(result, Path)
    assert result == (tmp_path / "out.bin").resolve()


def test_write_bytes_accepts_string_path(tmp_path: Path) -> None:
    """A str path works like a Path."""
    write_bytes(str(tmp_path / "out.bin"), b"x")

    assert (tmp_path / "out.bin").read_bytes() == b"x"


@pytest.mark.parametrize("use_draft", [True, False])
def test_write_bytes_creates_missing_folders(tmp_path: Path, use_draft) -> None:
    """The target's folder is guaranteed."""
    target = tmp_path / "a" / "b" / "out.bin"

    write_bytes(target, b"x", use_draft=use_draft)

    assert target.read_bytes() == b"x"


def test_write_bytes_large_data_roundtrip(tmp_path: Path) -> None:
    """A multi-megabyte write arrives intact."""
    data = bytes(range(256)) * 12_000
    target = tmp_path / "big.bin"

    write_bytes(target, data)

    assert target.read_bytes() == data


def test_write_bytes_through_a_symlink_replaces_the_real_file(tmp_path: Path) -> None:
    """The link stays a link; the file behind it is replaced."""
    real = tmp_path / "real.bin"
    real.write_bytes(b"old")
    link = tmp_path / "link.bin"
    try:
        link.symlink_to(real)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available here")

    write_bytes(link, b"new")

    assert link.is_symlink()
    assert real.read_bytes() == b"new"


# ----------------------------------------------------------------------
# overwrite
# ----------------------------------------------------------------------

@pytest.mark.parametrize("use_draft", [True, False])
def test_write_bytes_overwrite_false_refuses_an_existing_file(tmp_path: Path, use_draft) -> None:
    """The original stays untouched."""
    target = tmp_path / "out.bin"
    target.write_bytes(b"old")

    with pytest.raises(AlreadyExistsError) as info:
        write_bytes(target, b"new", overwrite=False, use_draft=use_draft)

    assert info.value.error_name == "FILE_WRITE_DESTINATION_EXISTS"
    assert isinstance(info.value, FileExistsError)
    assert target.read_bytes() == b"old"
    assert _drafts(tmp_path) == []


@pytest.mark.parametrize("use_draft", [True, False])
def test_write_bytes_overwrite_false_writes_a_missing_file(tmp_path: Path, use_draft) -> None:
    """overwrite=False only matters when something is there."""
    target = tmp_path / "out.bin"

    write_bytes(target, b"new", overwrite=False, use_draft=use_draft)

    assert target.read_bytes() == b"new"


def test_write_bytes_direct_mode_is_exact_when_the_file_appears_in_between(tmp_path: Path, monkeypatch) -> None:
    """Exclusive mode closes the check-then-write gap."""
    target = (tmp_path / "out.bin").resolve()
    target.write_bytes(b"someone was faster")
    monkeypatch.setattr(MODULE, "prepare_write_target", lambda path, operation, *, overwrite=True: target)

    with pytest.raises(AlreadyExistsError) as info:
        write_bytes(target, b"new", overwrite=False, use_draft=False)

    assert info.value.error_name == "FILE_WRITE_DESTINATION_EXISTS"
    assert target.read_bytes() == b"someone was faster"


def test_write_bytes_draft_mode_overwrite_false_is_best_effort(tmp_path: Path, monkeypatch) -> None:
    """Documented: os.replace overwrites silently if the file appears in the last millisecond."""
    target = (tmp_path / "out.bin").resolve()
    target.write_bytes(b"someone was faster")
    monkeypatch.setattr(MODULE, "prepare_write_target", lambda path, operation, *, overwrite=True: target)

    write_bytes(target, b"new", overwrite=False, use_draft=True)

    assert target.read_bytes() == b"new"


# ----------------------------------------------------------------------
# Failures
# ----------------------------------------------------------------------

@pytest.mark.parametrize("use_draft", [True, False])
def test_write_bytes_directory_at_target_is_a_state_error(tmp_path: Path, use_draft) -> None:
    """A directory can never be replaced by a file."""
    target = tmp_path / "folder"
    target.mkdir()

    with pytest.raises(StateError) as info:
        write_bytes(target, b"x", use_draft=use_draft)

    assert info.value.error_name == "FILE_WRITE_DESTINATION_IS_DIRECTORY"
    assert target.is_dir()
    assert _drafts(tmp_path) == []


def test_write_bytes_does_not_wrap_a_card_of_the_safe_writer_twice(tmp_path: Path, monkeypatch) -> None:
    """Cards may be OSError subclasses; `except OSError` must not wrap them a second time."""
    sentinel = AccessError(error_name="SAFE_WRITER_COMMIT_FAILED", exception=PermissionError)

    class _WriterRaisingACard:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            raise sentinel

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(MODULE, "SafeFileWriter", _WriterRaisingACard)

    with pytest.raises(AccessError) as info:
        write_bytes(tmp_path / "out.bin", b"x")

    assert info.value is sentinel


def test_write_bytes_raw_os_failure_in_the_draft_is_an_access_error(tmp_path: Path, monkeypatch) -> None:
    """A bare OSError while writing into the draft becomes a card."""
    class _WriterFailingOnWrite:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def write(self, data):
            raise OSError("disk full")

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(MODULE, "SafeFileWriter", _WriterFailingOnWrite)

    with pytest.raises(AccessError) as info:
        write_bytes(tmp_path / "out.bin", b"x")

    assert info.value.error_name == "FILE_WRITE_FAILED"
    assert isinstance(info.value, OSError)


def test_write_bytes_direct_os_failure_is_an_access_error(tmp_path: Path, monkeypatch) -> None:
    """A refused open in direct mode becomes a card."""
    target = tmp_path / "locked.bin"
    original_open = Path.open

    def refusing_open(self, *args, **kwargs):
        if self.name == "locked.bin":
            raise PermissionError("denied")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", refusing_open)

    with pytest.raises(AccessError) as info:
        write_bytes(target, b"x", use_draft=False)

    assert info.value.error_name == "FILE_WRITE_FAILED"
    assert isinstance(info.value, PermissionError)


# ----------------------------------------------------------------------
# sync
# ----------------------------------------------------------------------

def test_write_bytes_direct_sync_flushes_to_disk(tmp_path: Path, monkeypatch) -> None:
    """sync=True calls fsync in direct mode."""
    calls: list[int] = []
    monkeypatch.setattr(MODULE, "os", SimpleNamespace(fsync=lambda descriptor: calls.append(descriptor)))

    write_bytes(tmp_path / "out.bin", b"x", use_draft=False, sync=True)

    assert len(calls) == 1


def test_write_bytes_direct_without_sync_never_calls_fsync(tmp_path: Path, monkeypatch) -> None:
    """Durability is opt-in."""
    calls: list[int] = []
    monkeypatch.setattr(MODULE, "os", SimpleNamespace(fsync=lambda descriptor: calls.append(descriptor)))

    write_bytes(tmp_path / "out.bin", b"x", use_draft=False)

    assert calls == []


@pytest.mark.parametrize("sync", [False, True])
def test_write_bytes_draft_mode_forwards_sync_to_the_writer(tmp_path: Path, monkeypatch, sync) -> None:
    """The durability flag reaches SafeFileWriter."""
    received: list[dict] = []
    real_writer = MODULE.SafeFileWriter

    def recording_writer(target, **kwargs):
        received.append(kwargs)
        return real_writer(target, **kwargs)

    monkeypatch.setattr(MODULE, "SafeFileWriter", recording_writer)

    write_bytes(tmp_path / "out.bin", b"x", sync=sync)

    assert received == [{"mode": "wb", "sync": sync}]


# ----------------------------------------------------------------------
# Accepted data types
# ----------------------------------------------------------------------

@pytest.mark.parametrize("use_draft", [True, False])
@pytest.mark.parametrize("data", [bytearray(b"\x00ba"), memoryview(b"\x00mv"), memoryview(bytearray(b"\x00mba"))])
def test_write_bytes_accepts_any_bytes_like_object(tmp_path: Path, data, use_draft) -> None:
    """`bytes`, `bytearray` and `memoryview` are written as they are."""
    target = tmp_path / "out.bin"

    write_bytes(target, data, use_draft=use_draft)

    assert target.read_bytes() == bytes(data)


def test_write_bytes_rejects_text(tmp_path: Path) -> None:
    """Text is encoded by `write_text`, never guessed here."""
    with pytest.raises(ValidationError):
        write_bytes(tmp_path / "out.bin", "text")  # type: ignore[arg-type]

    assert not (tmp_path / "out.bin").exists()
