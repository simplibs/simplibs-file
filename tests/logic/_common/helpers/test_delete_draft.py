import importlib
import os
import stat
from pathlib import Path
from types import SimpleNamespace
import pytest
from simplibs.file.logic._common.helpers import delete_draft

# The package re-exports the function under the module's own name — fetch the real module for patching
MODULE = importlib.import_module("simplibs.file.logic._common.helpers.delete_draft")


def test_delete_draft_removes_the_file(tmp_path: Path) -> None:
    """The draft file is gone afterwards."""
    draft = tmp_path / ".a.txt.abcd1234.draft"
    draft.write_text("half", encoding="utf-8")

    delete_draft(draft)

    assert not draft.exists()


def test_delete_draft_returns_none(tmp_path: Path) -> None:
    """Cleanup has no result."""
    draft = tmp_path / ".a.txt.abcd1234.draft"
    draft.write_text("half", encoding="utf-8")

    assert delete_draft(draft) is None


def test_delete_draft_accepts_none() -> None:
    """Nothing was ever created — nothing to do."""
    assert delete_draft(None) is None


def test_delete_draft_missing_file_is_not_an_error(tmp_path: Path) -> None:
    """A draft that is already gone is fine."""
    delete_draft(tmp_path / ".a.txt.abcd1234.draft")


def test_delete_draft_leaves_other_files_alone(tmp_path: Path) -> None:
    """Only the given draft is removed."""
    draft = tmp_path / ".a.txt.abcd1234.draft"
    other = tmp_path / "a.txt"
    draft.write_text("half", encoding="utf-8")
    other.write_text("keep", encoding="utf-8")

    delete_draft(draft)

    assert other.read_text(encoding="utf-8") == "keep"


def test_delete_draft_swallows_os_errors(tmp_path: Path, monkeypatch) -> None:
    """A locked draft must never replace the ORIGINAL error with a less useful one."""
    draft = tmp_path / ".a.txt.abcd1234.draft"
    draft.write_text("half", encoding="utf-8")

    def refusing_unlink(self, *args, **kwargs):
        raise PermissionError("locked")

    monkeypatch.setattr(Path, "unlink", refusing_unlink)

    delete_draft(draft)

    assert draft.exists()


def test_delete_draft_directory_is_swallowed_and_kept(tmp_path: Path) -> None:
    """A directory at the draft path cannot be unlinked; the failure is silent."""
    folder = tmp_path / ".a.txt.abcd1234.draft"
    folder.mkdir()

    delete_draft(folder)

    assert folder.is_dir()


# ----------------------------------------------------------------------
# A read-only draft (the draft of a swap that failed on a read-only target)
# ----------------------------------------------------------------------

@pytest.mark.windows_only("a read-only file cannot be deleted")
def test_delete_draft_removes_a_read_only_draft_on_windows(tmp_path: Path) -> None:
    """The real thing: no orphan stays behind."""
    draft = tmp_path / ".a.txt.abcd1234.draft"
    draft.write_text("half", encoding="utf-8")
    os.chmod(draft, stat.S_IREAD)

    delete_draft(draft)

    assert not draft.exists()


def _unlink_refusing_first(monkeypatch, *, times: int) -> list[Path]:
    """Path.unlink that raises PermissionError `times` times, then works; returns the recorded calls."""
    original = Path.unlink
    calls: list[Path] = []

    def flaky(self, *args, **kwargs):
        calls.append(self)
        if len(calls) <= times:
            raise PermissionError("read-only")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", flaky)
    return calls


def test_delete_draft_clears_the_read_only_flag_and_retries_on_windows(tmp_path: Path, monkeypatch) -> None:
    """Platform faked, so it runs everywhere: chmod S_IWRITE, then a second unlink."""
    draft = tmp_path / ".a.txt.abcd1234.draft"
    draft.write_text("half", encoding="utf-8")
    chmods: list[tuple] = []
    monkeypatch.setattr(MODULE, "os", SimpleNamespace(name="nt", chmod=lambda path, mode: chmods.append((path, mode))))
    calls = _unlink_refusing_first(monkeypatch, times=1)

    delete_draft(draft)

    assert chmods == [(draft, stat.S_IWRITE)]
    assert len(calls) == 2
    assert not draft.exists()


def test_delete_draft_a_retry_that_still_fails_is_swallowed(tmp_path: Path, monkeypatch) -> None:
    """Even the second refusal must never replace the original error."""
    draft = tmp_path / ".a.txt.abcd1234.draft"
    draft.write_text("half", encoding="utf-8")
    monkeypatch.setattr(MODULE, "os", SimpleNamespace(name="nt", chmod=lambda path, mode: None))
    calls = _unlink_refusing_first(monkeypatch, times=99)

    delete_draft(draft)

    assert len(calls) == 2
    assert draft.exists()


def test_delete_draft_a_failing_chmod_is_swallowed(tmp_path: Path, monkeypatch) -> None:
    """Clearing the flag is best effort too."""
    draft = tmp_path / ".a.txt.abcd1234.draft"
    draft.write_text("half", encoding="utf-8")

    def refusing_chmod(path, mode):
        raise PermissionError("denied")

    monkeypatch.setattr(MODULE, "os", SimpleNamespace(name="nt", chmod=refusing_chmod))
    _unlink_refusing_first(monkeypatch, times=99)

    delete_draft(draft)

    assert draft.exists()


def test_delete_draft_does_not_touch_the_permissions_outside_windows(tmp_path: Path, monkeypatch) -> None:
    """On POSIX a PermissionError comes from the folder, and chmod on the draft would not help."""
    draft = tmp_path / ".a.txt.abcd1234.draft"
    draft.write_text("half", encoding="utf-8")
    chmods: list[tuple] = []
    monkeypatch.setattr(MODULE, "os", SimpleNamespace(name="posix", chmod=lambda path, mode: chmods.append((path, mode))))
    calls = _unlink_refusing_first(monkeypatch, times=99)

    delete_draft(draft)

    assert chmods == []
    assert len(calls) == 1
    assert draft.exists()


