import fnmatch
import importlib
import os
import re
from pathlib import Path
from types import SimpleNamespace
import pytest
from simplibs.file.logic.safe_writer import IGNORE_DRAFTS
from simplibs.file.logic._common.helpers import create_draft

MODULE = importlib.import_module("simplibs.file.logic._common.helpers.create_draft")

_DRAFT_NAME = re.compile(r"^\.(?P<base>.+)\.(?P<token>[0-9a-f]{8})\.draft$")


def _fake_os(open) -> SimpleNamespace:
    """The `os` names create_draft needs, with a replaceable `open`."""
    return SimpleNamespace(
        O_CREAT=os.O_CREAT,
        O_EXCL=os.O_EXCL,
        O_WRONLY=os.O_WRONLY,
        open=open,
        close=os.close,
    )


# ----------------------------------------------------------------------
# The draft itself
# ----------------------------------------------------------------------

def test_create_draft_creates_an_empty_file_next_to_the_target(tmp_path: Path) -> None:
    """The draft lives in the target's folder (required for an atomic swap) and starts empty."""
    target = tmp_path / "report.txt"

    draft = create_draft(target, append=False)

    assert draft.parent == target.parent
    assert draft.is_file()
    assert draft.read_bytes() == b""


def test_create_draft_name_follows_the_documented_pattern(tmp_path: Path) -> None:
    """The name is `.<name>.<8 hex>.draft`."""
    draft = create_draft(tmp_path / "report.txt", append=False)

    match = _DRAFT_NAME.match(draft.name)
    assert match is not None
    assert match.group("base") == "report.txt"


def test_create_draft_name_is_matched_by_ignore_drafts(tmp_path: Path) -> None:
    """Scanners using IGNORE_DRAFTS must skip every real draft name."""
    draft = create_draft(tmp_path / "report.txt", append=False)

    assert any(fnmatch.fnmatchcase(draft.name, pattern) for pattern in IGNORE_DRAFTS)


def test_create_draft_names_are_unique(tmp_path: Path) -> None:
    """Two drafts of the same target never share a name."""
    target = tmp_path / "report.txt"

    drafts = {create_draft(target, append=False) for _ in range(20)}

    assert len(drafts) == 20


def test_create_draft_does_not_touch_the_target(tmp_path: Path) -> None:
    """The final file is left exactly as it was."""
    target = tmp_path / "report.txt"
    target.write_text("original", encoding="utf-8")

    create_draft(target, append=False)

    assert target.read_text(encoding="utf-8") == "original"


def test_create_draft_target_does_not_have_to_exist(tmp_path: Path) -> None:
    """A brand new file can be drafted."""
    target = tmp_path / "new.txt"

    draft = create_draft(target, append=False)

    assert draft.exists()
    assert not target.exists()


# ----------------------------------------------------------------------
# Append
# ----------------------------------------------------------------------

def test_create_draft_append_copies_existing_content(tmp_path: Path) -> None:
    """Appending safely means: copy, append to the copy, swap."""
    target = tmp_path / "log.txt"
    target.write_bytes(b"line 1\n")

    draft = create_draft(target, append=True)

    assert draft.read_bytes() == b"line 1\n"
    assert target.read_bytes() == b"line 1\n"


def test_create_draft_without_append_starts_empty_even_when_target_exists(tmp_path: Path) -> None:
    """Overwrite mode never copies the old content."""
    target = tmp_path / "log.txt"
    target.write_bytes(b"line 1\n")

    draft = create_draft(target, append=False)

    assert draft.read_bytes() == b""


def test_create_draft_append_with_missing_target_starts_empty(tmp_path: Path) -> None:
    """There is nothing to continue after."""
    draft = create_draft(tmp_path / "new.txt", append=True)

    assert draft.read_bytes() == b""


def test_create_draft_append_with_directory_target_starts_empty(tmp_path: Path) -> None:
    """Only an existing regular file is copied."""
    folder = tmp_path / "folder"
    folder.mkdir()

    draft = create_draft(folder, append=True)

    assert draft.read_bytes() == b""


# ----------------------------------------------------------------------
# Names
# ----------------------------------------------------------------------

def test_create_draft_shortens_a_very_long_target_name(tmp_path: Path) -> None:
    """The base name is cut to 100 characters, so the result never exceeds the 255 limit."""
    target = tmp_path / ("a" * 300 + ".txt")

    draft = create_draft(target, append=False)

    assert draft.is_file()
    assert len(draft.name) == 1 + 100 + 1 + 8 + len(".draft")


def test_create_draft_name_of_a_long_multibyte_target_fits_the_byte_limit(tmp_path: Path) -> None:
    """On Linux and macOS the limit is 255 BYTES; 100 euro signs alone would be 300."""
    target = tmp_path / ("€" * 100 + ".txt")

    draft = create_draft(target, append=False)

    assert draft.is_file()
    assert len(os.fsencode(draft.name)) <= 255


def test_create_draft_handles_non_ascii_target_name(tmp_path: Path) -> None:
    """A long non-ASCII name still yields a creatable draft."""
    target = tmp_path / ("ž" * 100 + ".txt")

    draft = create_draft(target, append=False)

    assert draft.is_file()


# ----------------------------------------------------------------------
# Name clashes and failures
# ----------------------------------------------------------------------

def test_create_draft_retries_when_a_name_is_taken(tmp_path: Path, monkeypatch) -> None:
    """A clash is astronomically rare, but handled: the next random name is tried."""
    real_open = os.open
    calls: list[tuple] = []

    def flaky_open(*args, **kwargs):
        calls.append(args)
        if len(calls) <= 2:
            raise FileExistsError("taken")
        return real_open(*args, **kwargs)

    monkeypatch.setattr(MODULE, "os", _fake_os(flaky_open))

    draft = create_draft(tmp_path / "a.txt", append=False)

    assert draft.is_file()
    assert len(calls) == 3


def test_create_draft_gives_up_when_every_name_is_taken(tmp_path: Path, monkeypatch) -> None:
    """After the maximum number of attempts a FileExistsError naming the target is raised."""
    calls: list[tuple] = []

    def always_taken(*args, **kwargs):
        calls.append(args)
        raise FileExistsError("taken")

    monkeypatch.setattr(MODULE, "os", _fake_os(always_taken))
    target = tmp_path / "a.txt"

    with pytest.raises(FileExistsError) as info:
        create_draft(target, append=False)

    assert len(calls) == MODULE._MAX_ATTEMPTS
    assert str(target) in str(info.value)
    assert list(tmp_path.iterdir()) == []


def test_create_draft_other_os_errors_propagate_at_once(tmp_path: Path, monkeypatch) -> None:
    """Only a name clash is retried; a permission problem is real."""
    calls: list[tuple] = []

    def refusing_open(*args, **kwargs):
        calls.append(args)
        raise PermissionError("denied")

    monkeypatch.setattr(MODULE, "os", _fake_os(refusing_open))

    with pytest.raises(PermissionError):
        create_draft(tmp_path / "a.txt", append=False)

    assert len(calls) == 1


@pytest.mark.parametrize("error", [OSError("disk full"), KeyboardInterrupt()], ids=["OSError", "KeyboardInterrupt"])
def test_create_draft_failed_append_copy_leaves_nothing_behind(tmp_path: Path, monkeypatch, error) -> None:
    """A failure while copying the old content removes the draft again, and the error propagates."""
    target = tmp_path / "log.txt"
    target.write_bytes(b"line 1\n")

    def failing_copyfile(source, destination):
        raise error

    monkeypatch.setattr(MODULE, "shutil", SimpleNamespace(copyfile=failing_copyfile))

    with pytest.raises(type(error)):
        create_draft(target, append=True)

    assert [item.name for item in tmp_path.iterdir()] == ["log.txt"]
    assert target.read_bytes() == b"line 1\n"
