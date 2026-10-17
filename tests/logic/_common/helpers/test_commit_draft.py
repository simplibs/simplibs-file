import importlib
import os
import stat
from pathlib import Path
from types import SimpleNamespace
import pytest
from simplibs.file.logic._common.helpers import commit_draft

MODULE = importlib.import_module("simplibs.file.logic._common.helpers.commit_draft")

_POSIX_ONLY = pytest.mark.posix_only("permission bits")


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


# ----------------------------------------------------------------------
# The swap
# ----------------------------------------------------------------------

def test_commit_draft_replaces_the_target(tmp_path: Path) -> None:
    """The target gets the draft's content and the draft file disappears."""
    target = tmp_path / "target.txt"
    draft = tmp_path / ".target.txt.abcd1234.draft"
    target.write_text("old", encoding="utf-8")
    draft.write_text("new", encoding="utf-8")

    commit_draft(draft, target)

    assert target.read_text(encoding="utf-8") == "new"
    assert not draft.exists()


def test_commit_draft_creates_a_missing_target(tmp_path: Path) -> None:
    """A brand new file is simply put in place."""
    target = tmp_path / "target.txt"
    draft = tmp_path / ".target.txt.abcd1234.draft"
    draft.write_text("new", encoding="utf-8")

    commit_draft(draft, target)

    assert target.read_text(encoding="utf-8") == "new"


def test_commit_draft_returns_none(tmp_path: Path) -> None:
    """The commit has no result."""
    target = tmp_path / "target.txt"
    draft = tmp_path / ".target.txt.abcd1234.draft"
    draft.write_text("new", encoding="utf-8")

    assert commit_draft(draft, target) is None


def test_commit_draft_directory_at_target_fails_and_keeps_both(tmp_path: Path) -> None:
    """The helper raises (the caller builds the card) and discards nothing."""
    folder = tmp_path / "folder"
    folder.mkdir()
    draft = tmp_path / ".folder.abcd1234.draft"
    draft.write_text("new", encoding="utf-8")

    with pytest.raises(OSError):
        commit_draft(draft, folder, attempts=1)

    assert folder.is_dir()
    assert draft.exists()


def test_commit_draft_forwards_attempts_and_delay_to_the_swap(tmp_path: Path, monkeypatch) -> None:
    """The Windows retry settings reach replace_with_retry unchanged."""
    calls: list[tuple] = []

    def recording_replace(source, destination, **kwargs):
        calls.append((source, destination, kwargs))

    monkeypatch.setattr(MODULE, "replace_with_retry", recording_replace)
    target = tmp_path / "target.txt"
    draft = tmp_path / ".target.txt.abcd1234.draft"

    commit_draft(draft, target, attempts=3, delay=0.2)

    assert calls == [(draft, target, {"attempts": 3, "delay": 0.2})]


# ----------------------------------------------------------------------
# Permissions
# ----------------------------------------------------------------------

@_POSIX_ONLY
def test_commit_draft_keeps_the_mode_of_the_replaced_file(tmp_path: Path) -> None:
    """A 0o600 secrets file must not silently become 0o644."""
    target = tmp_path / "target.txt"
    draft = tmp_path / ".target.txt.abcd1234.draft"
    target.write_text("old", encoding="utf-8")
    draft.write_text("new", encoding="utf-8")
    os.chmod(target, 0o600)
    os.chmod(draft, 0o644)

    commit_draft(draft, target)

    assert _mode(target) == 0o600


@_POSIX_ONLY
def test_commit_draft_keep_mode_false_keeps_the_mode_of_the_draft(tmp_path: Path) -> None:
    """A copy carries the permissions of its SOURCE, not of the file it replaces."""
    target = tmp_path / "target.txt"
    draft = tmp_path / ".target.txt.abcd1234.draft"
    target.write_text("old", encoding="utf-8")
    draft.write_text("new", encoding="utf-8")
    os.chmod(target, 0o600)
    os.chmod(draft, 0o640)

    commit_draft(draft, target, keep_mode=False)

    assert _mode(target) == 0o640


def test_commit_draft_failing_copymode_does_not_stop_the_swap(tmp_path: Path, monkeypatch) -> None:
    """Copying the mode is best effort."""
    def failing_copymode(source, destination):
        raise OSError("not supported")

    monkeypatch.setattr(MODULE, "shutil", SimpleNamespace(copymode=failing_copymode))
    target = tmp_path / "target.txt"
    draft = tmp_path / ".target.txt.abcd1234.draft"
    target.write_text("old", encoding="utf-8")
    draft.write_text("new", encoding="utf-8")

    commit_draft(draft, target)

    assert target.read_text(encoding="utf-8") == "new"


# ----------------------------------------------------------------------
# Durability
# ----------------------------------------------------------------------

def _fake_os(*, name: str, fsync, open=os.open, close=os.close) -> SimpleNamespace:
    """The `os` names commit_draft needs."""
    return SimpleNamespace(name=name, fsync=fsync, open=open, close=close, O_RDONLY=os.O_RDONLY)


def test_commit_draft_without_sync_never_calls_fsync(tmp_path: Path, monkeypatch) -> None:
    """Durability is opt-in."""
    calls: list[int] = []
    monkeypatch.setattr(MODULE, "os", _fake_os(name=os.name, fsync=calls.append))
    target = tmp_path / "target.txt"
    draft = tmp_path / ".target.txt.abcd1234.draft"
    draft.write_text("new", encoding="utf-8")

    commit_draft(draft, target)

    assert calls == []


def test_commit_draft_sync_flushes_the_draft_and_on_posix_the_folder(tmp_path: Path, monkeypatch) -> None:
    """The draft is synced before the swap; the folder after it, where the OS allows."""
    calls: list[int] = []

    def recording_fsync(descriptor):
        calls.append(descriptor)
        os.fsync(descriptor)

    monkeypatch.setattr(MODULE, "os", _fake_os(name=os.name, fsync=recording_fsync))
    target = tmp_path / "target.txt"
    draft = tmp_path / ".target.txt.abcd1234.draft"
    draft.write_text("new", encoding="utf-8")

    commit_draft(draft, target, sync=True)

    assert len(calls) == (1 if os.name == "nt" else 2)
    assert target.read_text(encoding="utf-8") == "new"


def test_commit_draft_sync_on_posix_opens_syncs_and_closes_the_folder(tmp_path: Path, monkeypatch) -> None:
    """Persisting the rename: the target's folder is opened read-only, synced, then closed.

    The platform is faked, so this runs on Windows too (where a folder cannot really be opened).
    """
    events: list[tuple] = []
    folder_descriptor = 123456

    def fake_open(path, flags):
        events.append(("open", Path(path), flags))
        return folder_descriptor

    monkeypatch.setattr(
        MODULE,
        "os",
        _fake_os(
            name="posix",
            fsync=lambda descriptor: events.append(("fsync", descriptor)),
            open=fake_open,
            close=lambda descriptor: events.append(("close", descriptor)),
        ),
    )
    target = tmp_path / "target.txt"
    draft = tmp_path / ".target.txt.abcd1234.draft"
    draft.write_text("new", encoding="utf-8")

    commit_draft(draft, target, sync=True)

    assert len(events) == 4
    assert events[0][0] == "fsync"                                   # the draft itself, before the swap
    assert events[1:] == [
        ("open", target.parent, os.O_RDONLY),
        ("fsync", folder_descriptor),
        ("close", folder_descriptor),
    ]
    assert target.read_text(encoding="utf-8") == "new"


def test_commit_draft_closes_the_folder_even_when_its_sync_fails(tmp_path: Path, monkeypatch) -> None:
    """A failing fsync of the folder is ignored — and the descriptor is still released."""
    closed: list[int] = []
    folder_descriptor = 123456

    def fake_fsync(descriptor):
        if descriptor == folder_descriptor:
            raise OSError("not supported here")

    monkeypatch.setattr(
        MODULE,
        "os",
        _fake_os(
            name="posix",
            fsync=fake_fsync,
            open=lambda path, flags: folder_descriptor,
            close=closed.append,
        ),
    )
    target = tmp_path / "target.txt"
    draft = tmp_path / ".target.txt.abcd1234.draft"
    draft.write_text("new", encoding="utf-8")

    commit_draft(draft, target, sync=True)

    assert closed == [folder_descriptor]
    assert target.read_text(encoding="utf-8") == "new"


def test_commit_draft_failing_folder_sync_is_ignored(tmp_path: Path, monkeypatch) -> None:
    """Persisting the rename is best effort; its failure must not undo a finished swap."""
    def refusing_open(*args, **kwargs):
        raise OSError("cannot open a folder")

    monkeypatch.setattr(MODULE, "os", _fake_os(name="posix", fsync=os.fsync, open=refusing_open))
    target = tmp_path / "target.txt"
    draft = tmp_path / ".target.txt.abcd1234.draft"
    draft.write_text("new", encoding="utf-8")

    commit_draft(draft, target, sync=True)

    assert target.read_text(encoding="utf-8") == "new"


# ----------------------------------------------------------------------
# Windows: the read-only flag
# ----------------------------------------------------------------------

def _writable(path: Path) -> bool:
    return bool(path.stat().st_mode & stat.S_IWRITE)


@pytest.mark.windows_only("a read-only target blocks the swap")
def test_commit_draft_read_only_target_fails_cleanly_and_keeps_both(tmp_path: Path) -> None:
    """The swap fails with an OSError; the old file and the draft are both still there."""
    target = tmp_path / "target.txt"
    draft = tmp_path / ".target.txt.abcd1234.draft"
    target.write_text("old", encoding="utf-8")
    draft.write_text("new", encoding="utf-8")
    os.chmod(target, stat.S_IREAD)

    try:
        with pytest.raises(PermissionError):
            commit_draft(draft, target, attempts=2, delay=0)
    finally:
        os.chmod(target, stat.S_IREAD | stat.S_IWRITE)

    assert target.read_text(encoding="utf-8") == "old"
    assert draft.exists()


@pytest.mark.windows_only("copymode carries the read-only flag")
def test_commit_draft_keeps_the_writable_state_of_the_replaced_file_on_windows(tmp_path: Path) -> None:
    """The Windows counterpart of the POSIX mode test: a writable file stays writable."""
    target = tmp_path / "target.txt"
    draft = tmp_path / ".target.txt.abcd1234.draft"
    target.write_text("old", encoding="utf-8")
    draft.write_text("new", encoding="utf-8")
    os.chmod(draft, stat.S_IREAD)

    commit_draft(draft, target)

    assert target.read_text(encoding="utf-8") == "new"
    assert _writable(target)


@pytest.mark.windows_only("copymode carries the read-only flag")
def test_commit_draft_keep_mode_false_keeps_the_read_only_flag_of_the_draft(tmp_path: Path) -> None:
    """A copy carries the flag of its SOURCE, not of the file it replaces."""
    target = tmp_path / "target.txt"
    draft = tmp_path / ".target.txt.abcd1234.draft"
    target.write_text("old", encoding="utf-8")
    draft.write_text("new", encoding="utf-8")
    os.chmod(draft, stat.S_IREAD)

    try:
        commit_draft(draft, target, keep_mode=False)
        assert not _writable(target)
    finally:
        os.chmod(target, stat.S_IREAD | stat.S_IWRITE)
