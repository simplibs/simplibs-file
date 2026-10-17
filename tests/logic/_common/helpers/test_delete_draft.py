from pathlib import Path
from simplibs.file.logic._common.helpers import delete_draft


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
