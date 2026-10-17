import importlib
from pathlib import Path
from types import SimpleNamespace
import pytest
from simplibs.exception import AccessError, StateError
from simplibs.file.logic.write import append_bytes

MODULE = importlib.import_module("simplibs.file.logic.write.append_bytes")


def _drafts(folder: Path) -> list[Path]:
    return sorted(folder.glob(".*.draft"))


@pytest.mark.parametrize("use_draft", [True, False])
def test_append_bytes_creates_a_missing_file(tmp_path: Path, use_draft) -> None:
    """Appending to nothing is writing."""
    target = tmp_path / "log.bin"

    append_bytes(target, b"one", use_draft=use_draft)

    assert target.read_bytes() == b"one"


@pytest.mark.parametrize("use_draft", [True, False])
def test_append_bytes_adds_after_the_existing_content(tmp_path: Path, use_draft) -> None:
    """The old content stays, the new bytes follow."""
    target = tmp_path / "log.bin"
    target.write_bytes(b"one")

    append_bytes(target, b"two", use_draft=use_draft)

    assert target.read_bytes() == b"onetwo"
    assert _drafts(tmp_path) == []


@pytest.mark.parametrize("use_draft", [True, False])
def test_append_bytes_several_appends_accumulate(tmp_path: Path, use_draft) -> None:
    """Every append adds to the end."""
    target = tmp_path / "log.bin"

    for chunk in (b"a", b"b", b"c"):
        append_bytes(target, chunk, use_draft=use_draft)

    assert target.read_bytes() == b"abc"


@pytest.mark.parametrize("use_draft", [True, False])
def test_append_bytes_empty_data_creates_an_empty_file(tmp_path: Path, use_draft) -> None:
    """An empty append still creates the file."""
    target = tmp_path / "empty.bin"

    append_bytes(target, b"", use_draft=use_draft)

    assert target.read_bytes() == b""


def test_append_bytes_defaults_to_the_in_place_append(tmp_path: Path, monkeypatch) -> None:
    """A draft append would copy the whole file on every call, so it is opt-in."""
    used: list[bool] = []
    monkeypatch.setattr(MODULE, "SafeFileWriter", lambda *args, **kwargs: used.append(True))

    append_bytes(tmp_path / "log.bin", b"x")

    assert used == []


def test_append_bytes_returns_the_normalized_path(tmp_path: Path) -> None:
    """The result is the absolute, resolved target."""
    result = append_bytes(tmp_path / "log.bin", b"x")

    assert result == (tmp_path / "log.bin").resolve()


def test_append_bytes_accepts_string_path(tmp_path: Path) -> None:
    """A str path works like a Path."""
    append_bytes(str(tmp_path / "log.bin"), b"x")

    assert (tmp_path / "log.bin").read_bytes() == b"x"


def test_append_bytes_creates_missing_folders(tmp_path: Path) -> None:
    """The target's folder is guaranteed."""
    target = tmp_path / "a" / "b" / "log.bin"

    append_bytes(target, b"x")

    assert target.read_bytes() == b"x"


@pytest.mark.parametrize("use_draft", [True, False])
def test_append_bytes_directory_at_target_is_a_state_error(tmp_path: Path, use_draft) -> None:
    """A directory cannot be appended to."""
    target = tmp_path / "folder"
    target.mkdir()

    with pytest.raises(StateError) as info:
        append_bytes(target, b"x", use_draft=use_draft)

    assert info.value.error_name == "FILE_APPEND_DESTINATION_IS_DIRECTORY"
    assert target.is_dir()


def test_append_bytes_draft_mode_uses_append_mode_of_the_writer(tmp_path: Path, monkeypatch) -> None:
    """The draft starts as a copy of the old content, so the writer is opened in "ab"."""
    received: list[dict] = []
    real_writer = MODULE.SafeFileWriter

    def recording_writer(target, **kwargs):
        received.append(kwargs)
        return real_writer(target, **kwargs)

    monkeypatch.setattr(MODULE, "SafeFileWriter", recording_writer)

    append_bytes(tmp_path / "log.bin", b"x", use_draft=True, sync=True)

    assert received == [{"mode": "ab", "sync": True}]


def test_append_bytes_does_not_wrap_a_card_of_the_safe_writer_twice(tmp_path: Path, monkeypatch) -> None:
    """Cards may be OSError subclasses; they must pass through untouched."""
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
        append_bytes(tmp_path / "log.bin", b"x", use_draft=True)

    assert info.value is sentinel


def test_append_bytes_raw_os_failure_in_the_draft_is_an_access_error(tmp_path: Path, monkeypatch) -> None:
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
        append_bytes(tmp_path / "log.bin", b"x", use_draft=True)

    assert info.value.error_name == "FILE_APPEND_FAILED"


def test_append_bytes_direct_os_failure_is_an_access_error(tmp_path: Path, monkeypatch) -> None:
    """A refused open in direct mode becomes a card."""
    original_open = Path.open

    def refusing_open(self, *args, **kwargs):
        if self.name == "locked.bin":
            raise PermissionError("denied")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", refusing_open)

    with pytest.raises(AccessError) as info:
        append_bytes(tmp_path / "locked.bin", b"x")

    assert info.value.error_name == "FILE_APPEND_FAILED"
    assert isinstance(info.value, PermissionError)


def test_append_bytes_direct_sync_flushes_to_disk(tmp_path: Path, monkeypatch) -> None:
    """sync=True calls fsync in direct mode."""
    calls: list[int] = []
    monkeypatch.setattr(MODULE, "os", SimpleNamespace(fsync=lambda descriptor: calls.append(descriptor)))

    append_bytes(tmp_path / "log.bin", b"x", sync=True)

    assert len(calls) == 1
