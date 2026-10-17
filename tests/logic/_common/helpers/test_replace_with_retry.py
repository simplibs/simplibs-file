import importlib
from pathlib import Path
from types import SimpleNamespace
import pytest
from simplibs.file.logic._common.helpers import replace_with_retry

# The package re-exports the function under the module's own name — fetch the real module for patching
MODULE = importlib.import_module("simplibs.file.logic._common.helpers.replace_with_retry")


def _replace_failing(failures: int, error: type[OSError] = PermissionError):
    """A fake os.replace that fails `failures` times, then succeeds; records every call."""
    calls: list[tuple] = []

    def replace(source, destination):
        calls.append((source, destination))
        if len(calls) <= failures:
            raise error("locked")

    return replace, calls


def _patch_platform(monkeypatch, name: str, replace) -> list[float]:
    """Replace the module's `os` and `time` with fakes; return the list of recorded pauses."""
    sleeps: list[float] = []
    monkeypatch.setattr(MODULE, "os", SimpleNamespace(name=name, replace=replace))
    monkeypatch.setattr(MODULE, "time", SimpleNamespace(sleep=sleeps.append))
    return sleeps


# ----------------------------------------------------------------------
# Real filesystem
# ----------------------------------------------------------------------

def test_replace_with_retry_replaces_existing_file(tmp_path: Path) -> None:
    """The destination gets the content of the source and the source disappears."""
    source = tmp_path / "draft.tmp"
    destination = tmp_path / "target.txt"
    source.write_text("new", encoding="utf-8")
    destination.write_text("old", encoding="utf-8")

    replace_with_retry(source, destination)

    assert destination.read_text(encoding="utf-8") == "new"
    assert not source.exists()


def test_replace_with_retry_creates_missing_destination(tmp_path: Path) -> None:
    """A destination that does not exist yet is simply created."""
    source = tmp_path / "draft.tmp"
    destination = tmp_path / "target.txt"
    source.write_text("new", encoding="utf-8")

    replace_with_retry(source, destination)

    assert destination.read_text(encoding="utf-8") == "new"


def test_replace_with_retry_missing_source_raises(tmp_path: Path) -> None:
    """A missing source is a real OSError, raised at once."""
    with pytest.raises(OSError):
        replace_with_retry(tmp_path / "nothing.tmp", tmp_path / "target.txt")


# ----------------------------------------------------------------------
# Retry behaviour (faked platform)
# ----------------------------------------------------------------------

def test_replace_with_retry_succeeds_on_third_attempt_on_windows(monkeypatch) -> None:
    """Two short locks are hidden by the retry; pauses grow with every attempt."""
    replace, calls = _replace_failing(failures=2)
    sleeps = _patch_platform(monkeypatch, "nt", replace)

    replace_with_retry(Path("a"), Path("b"))

    assert len(calls) == 3
    assert sleeps == pytest.approx([0.05, 0.10])


def test_replace_with_retry_raises_after_all_attempts_on_windows(monkeypatch) -> None:
    """A lock that outlasts every attempt is raised, with no pause after the last try."""
    replace, calls = _replace_failing(failures=999)
    sleeps = _patch_platform(monkeypatch, "nt", replace)

    with pytest.raises(PermissionError):
        replace_with_retry(Path("a"), Path("b"), attempts=3)

    assert len(calls) == 3
    assert len(sleeps) == 2


def test_replace_with_retry_pause_grows_with_delay_and_attempt(monkeypatch) -> None:
    """The pause is `delay * attempt`."""
    replace, _ = _replace_failing(failures=999)
    sleeps = _patch_platform(monkeypatch, "nt", replace)

    with pytest.raises(PermissionError):
        replace_with_retry(Path("a"), Path("b"), attempts=4, delay=0.1)

    assert sleeps == pytest.approx([0.1, 0.2, 0.3])


def test_replace_with_retry_single_attempt_on_windows_raises_at_once(monkeypatch) -> None:
    """With attempts=1 there is nothing to retry and nothing to wait for."""
    replace, calls = _replace_failing(failures=999)
    sleeps = _patch_platform(monkeypatch, "nt", replace)

    with pytest.raises(PermissionError):
        replace_with_retry(Path("a"), Path("b"), attempts=1)

    assert len(calls) == 1
    assert sleeps == []


def test_replace_with_retry_makes_single_attempt_on_posix(monkeypatch) -> None:
    """Outside Windows a PermissionError is real and raised at once."""
    replace, calls = _replace_failing(failures=999)
    sleeps = _patch_platform(monkeypatch, "posix", replace)

    with pytest.raises(PermissionError):
        replace_with_retry(Path("a"), Path("b"))

    assert len(calls) == 1
    assert sleeps == []


@pytest.mark.parametrize("error", [FileNotFoundError, IsADirectoryError, OSError])
def test_replace_with_retry_does_not_retry_other_errors(monkeypatch, error) -> None:
    """Only a PermissionError can be a short lock; anything else fails at once, even on Windows."""
    replace, calls = _replace_failing(failures=999, error=error)
    sleeps = _patch_platform(monkeypatch, "nt", replace)

    with pytest.raises(error):
        replace_with_retry(Path("a"), Path("b"))

    assert len(calls) == 1
    assert sleeps == []


@pytest.mark.parametrize("attempts", [0, -3])
def test_replace_with_retry_makes_at_least_one_attempt(monkeypatch, attempts) -> None:
    """A nonsensical `attempts` means a single try — never a silent "nothing happened"."""
    replace, calls = _replace_failing(failures=0)
    sleeps = _patch_platform(monkeypatch, "nt", replace)

    replace_with_retry(Path("a"), Path("b"), attempts=attempts)

    assert calls == [(Path("a"), Path("b"))]
    assert sleeps == []


@pytest.mark.parametrize("attempts", [0, -3])
def test_replace_with_retry_with_no_attempts_still_replaces_the_file(tmp_path: Path, attempts) -> None:
    """Nothing is skipped on the real filesystem either."""
    source = tmp_path / "draft.tmp"
    destination = tmp_path / "target.txt"
    source.write_text("new", encoding="utf-8")
    destination.write_text("old", encoding="utf-8")

    replace_with_retry(source, destination, attempts=attempts)

    assert destination.read_text(encoding="utf-8") == "new"
    assert not source.exists()


@pytest.mark.parametrize("attempts", [0, 1])
def test_replace_with_retry_single_try_failure_is_raised(monkeypatch, attempts) -> None:
    """The one and only try fails for good — on Windows too."""
    replace, calls = _replace_failing(failures=999)
    sleeps = _patch_platform(monkeypatch, "nt", replace)

    with pytest.raises(PermissionError):
        replace_with_retry(Path("a"), Path("b"), attempts=attempts)

    assert len(calls) == 1
    assert sleeps == []


def test_replace_with_retry_passes_paths_through_unchanged(monkeypatch) -> None:
    """Source and destination reach os.replace exactly as given."""
    replace, calls = _replace_failing(failures=0)
    _patch_platform(monkeypatch, "nt", replace)
    source, destination = Path("draft.tmp"), Path("target.txt")

    replace_with_retry(source, destination)

    assert calls == [(source, destination)]
