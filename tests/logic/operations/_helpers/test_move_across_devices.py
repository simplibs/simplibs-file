import importlib
import os
from pathlib import Path
import pytest
from simplibs.file.logic.operations._helpers import move_across_devices

MODULE = importlib.import_module("simplibs.file.logic.operations._helpers.move_across_devices")


def _drafts(folder: Path) -> list[Path]:
    return sorted(folder.glob(".*.draft"))


def test_move_across_devices_moves_the_content_and_removes_the_source(tmp_path: Path) -> None:
    """Copy fully, THEN delete."""
    source = tmp_path / "source.bin"
    destination = tmp_path / "other" / "moved.bin"
    destination.parent.mkdir()
    source.write_bytes(b"\x00\xffdata")

    move_across_devices(source, destination)

    assert destination.read_bytes() == b"\x00\xffdata"
    assert not source.exists()
    assert _drafts(destination.parent) == []


def test_move_across_devices_returns_none(tmp_path: Path) -> None:
    """The move has no result."""
    source = tmp_path / "source.bin"
    source.write_bytes(b"x")

    assert move_across_devices(source, tmp_path / "moved.bin") is None


def test_move_across_devices_replaces_an_existing_destination(tmp_path: Path) -> None:
    """The destination becomes the complete copy."""
    source = tmp_path / "source.bin"
    destination = tmp_path / "moved.bin"
    source.write_bytes(b"new")
    destination.write_bytes(b"old content that is longer")

    move_across_devices(source, destination)

    assert destination.read_bytes() == b"new"
    assert not source.exists()


def test_move_across_devices_keeps_the_modification_time(tmp_path: Path) -> None:
    """The atomic copy carries the source's metadata."""
    source = tmp_path / "source.bin"
    source.write_bytes(b"x")
    os.utime(source, (1_600_000_000, 1_600_000_000))

    move_across_devices(source, tmp_path / "moved.bin")

    assert int((tmp_path / "moved.bin").stat().st_mtime) == 1_600_000_000


def test_move_across_devices_refuses_a_symlink_and_changes_nothing(tmp_path: Path, symlink_or_skip) -> None:
    """Silently turning a link into a regular file would change what it is."""
    real = tmp_path / "real.bin"
    real.write_bytes(b"content")
    link = tmp_path / "link.bin"
    symlink_or_skip(link, real)

    with pytest.raises(OSError, match="symbolic link"):
        move_across_devices(link, tmp_path / "moved.bin")

    assert link.is_symlink()
    assert real.read_bytes() == b"content"
    assert not (tmp_path / "moved.bin").exists()


def test_move_across_devices_failed_copy_keeps_the_source(tmp_path: Path, monkeypatch) -> None:
    """A failure at any point leaves at least one complete file."""
    source = tmp_path / "source.bin"
    destination = tmp_path / "moved.bin"
    source.write_bytes(b"precious")

    def failing_copy(src, dst, *, sync=False):
        raise OSError("disk full")

    monkeypatch.setattr(MODULE, "copy_atomically", failing_copy)

    with pytest.raises(OSError, match="disk full"):
        move_across_devices(source, destination)

    assert source.read_bytes() == b"precious"
    assert not destination.exists()


def test_move_across_devices_unremovable_source_leaves_both_files(tmp_path: Path, monkeypatch) -> None:
    """The worst case: copy done, source locked — two files, never none."""
    source = tmp_path / "source.bin"
    destination = tmp_path / "moved.bin"
    source.write_bytes(b"precious")
    original_unlink = Path.unlink

    def refusing_unlink(self, *args, **kwargs):
        if self.name == "source.bin":
            raise PermissionError("locked")
        return original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", refusing_unlink)

    with pytest.raises(PermissionError):
        move_across_devices(source, destination)

    assert source.read_bytes() == b"precious"
    assert destination.read_bytes() == b"precious"


@pytest.mark.parametrize("sync", [False, True])
def test_move_across_devices_forwards_sync_to_the_copy(tmp_path: Path, monkeypatch, sync) -> None:
    """The durability flag reaches copy_atomically, so the source is removed only after a flushed copy."""
    received: list[bool] = []
    original_copy = MODULE.copy_atomically

    def recording_copy(src, dst, *, sync=False):
        received.append(sync)
        original_copy(src, dst, sync=sync)

    monkeypatch.setattr(MODULE, "copy_atomically", recording_copy)
    source = tmp_path / "source.bin"
    source.write_bytes(b"x")

    move_across_devices(source, tmp_path / "moved.bin", sync=sync)

    assert received == [sync]
