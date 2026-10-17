import importlib
import os
import stat
from pathlib import Path
import pytest
from simplibs.exception import AccessError, StateError
from simplibs.file.logic.safe_writer import SafeFileWriter

# The package re-exports the class under the module's own name — fetch the real module for patching
MODULE = importlib.import_module("simplibs.file.logic.safe_writer.SafeFileWriter")


def _drafts(folder: Path) -> list[Path]:
    """Every draft file left in the folder."""
    return sorted(folder.glob(".*.draft"))


class _FailingHandle:
    """A handle that accepts writes but cannot be closed — a full disk shows up at close."""

    def write(self, data) -> int:
        return len(data)

    def close(self) -> None:
        raise OSError("disk full")


# ----------------------------------------------------------------------
# Writing
# ----------------------------------------------------------------------

def test_safe_file_writer_writes_a_new_text_file(tmp_path: Path) -> None:
    """The handle is open inside the block, closed after it, and no draft remains."""
    target = tmp_path / "out.txt"

    with SafeFileWriter(target) as handle:
        assert not handle.closed
        handle.write("hello\n")

    assert handle.closed
    assert target.read_bytes() == b"hello\n"
    assert _drafts(tmp_path) == []


def test_safe_file_writer_writes_binary(tmp_path: Path) -> None:
    """Binary mode writes the bytes exactly."""
    target = tmp_path / "out.bin"

    with SafeFileWriter(target, mode="wb") as handle:
        handle.write(b"\x00\xff\x10")

    assert target.read_bytes() == b"\x00\xff\x10"


def test_safe_file_writer_accepts_string_path(tmp_path: Path) -> None:
    """A str path works like a Path."""
    target = tmp_path / "out.txt"

    with SafeFileWriter(str(target)) as handle:
        handle.write("x")

    assert target.read_text(encoding="utf-8") == "x"


def test_safe_file_writer_creates_missing_folders(tmp_path: Path) -> None:
    """The target's folder is guaranteed."""
    target = tmp_path / "a" / "b" / "out.txt"

    with SafeFileWriter(target) as handle:
        handle.write("x")

    assert target.read_text(encoding="utf-8") == "x"


def test_safe_file_writer_large_binary_roundtrip(tmp_path: Path) -> None:
    """A multi-megabyte write arrives intact."""
    data = bytes(range(256)) * 12_000
    target = tmp_path / "big.bin"

    with SafeFileWriter(target, mode="wb") as handle:
        handle.write(data)

    assert target.read_bytes() == data


def test_safe_file_writer_sync_mode_writes_normally(tmp_path: Path) -> None:
    """sync=True only adds durability, not different behaviour."""
    target = tmp_path / "out.txt"

    with SafeFileWriter(target, sync=True) as handle:
        handle.write("durable")

    assert target.read_text(encoding="utf-8") == "durable"
    assert _drafts(tmp_path) == []


# ----------------------------------------------------------------------
# Atomic replacement
# ----------------------------------------------------------------------

def test_safe_file_writer_target_keeps_old_content_until_the_block_ends(tmp_path: Path) -> None:
    """Writes go into a private draft; a reader sees the old file until the swap."""
    target = tmp_path / "out.txt"
    target.write_text("old", encoding="utf-8")

    with SafeFileWriter(target) as handle:
        handle.write("new")
        handle.flush()
        assert target.read_text(encoding="utf-8") == "old"
        assert len(_drafts(tmp_path)) == 1

    assert target.read_text(encoding="utf-8") == "new"
    assert _drafts(tmp_path) == []


def test_safe_file_writer_exception_in_block_keeps_original_and_removes_draft(tmp_path: Path) -> None:
    """A failing block leaves the original exactly as it was, and the exception propagates untouched."""
    target = tmp_path / "out.txt"
    target.write_text("old", encoding="utf-8")

    with pytest.raises(ValueError, match="boom"):
        with SafeFileWriter(target) as handle:
            handle.write("half")
            raise ValueError("boom")

    assert target.read_text(encoding="utf-8") == "old"
    assert _drafts(tmp_path) == []


def test_safe_file_writer_exception_in_block_does_not_create_the_target(tmp_path: Path) -> None:
    """A failed first write leaves no file at all."""
    target = tmp_path / "out.txt"

    with pytest.raises(RuntimeError):
        with SafeFileWriter(target) as handle:
            handle.write("half")
            raise RuntimeError("boom")

    assert not target.exists()
    assert _drafts(tmp_path) == []


def test_safe_file_writer_never_suppresses_an_exception(tmp_path: Path) -> None:
    """__exit__ always lets the exception through."""
    target = tmp_path / "out.txt"
    raised = False

    try:
        with SafeFileWriter(target):
            raise KeyError("boom")
    except KeyError:
        raised = True

    assert raised


def test_safe_file_writer_two_writers_use_distinct_drafts(tmp_path: Path) -> None:
    """No interleaving: each writer has its own draft; the last commit wins."""
    target = tmp_path / "out.txt"

    with SafeFileWriter(target) as first_handle:
        first_handle.write("one")
        with SafeFileWriter(target) as second_handle:
            second_handle.write("two")
            assert len(_drafts(tmp_path)) == 2
        assert target.read_text(encoding="utf-8") == "two"

    assert target.read_text(encoding="utf-8") == "one"
    assert _drafts(tmp_path) == []


def test_safe_file_writer_instance_can_be_used_again(tmp_path: Path) -> None:
    """Entering a used instance again simply creates a new draft."""
    target = tmp_path / "out.txt"
    writer = SafeFileWriter(target)

    with writer as handle:
        handle.write("a")
    with writer as handle:
        handle.write("b")

    assert target.read_text(encoding="utf-8") == "b"
    assert _drafts(tmp_path) == []


def test_safe_file_writer_exit_without_enter_does_nothing(tmp_path: Path) -> None:
    """Called by hand on a fresh writer, `__exit__` has no draft to commit and touches nothing."""
    target = tmp_path / "out.txt"
    target.write_text("old", encoding="utf-8")
    writer = SafeFileWriter(target)

    assert writer.__exit__(None, None, None) is False

    assert target.read_text(encoding="utf-8") == "old"
    assert _drafts(tmp_path) == []


def test_safe_file_writer_exit_without_enter_never_suppresses_an_exception(tmp_path: Path) -> None:
    """Even with nothing to finish, an exception is left to propagate."""
    writer = SafeFileWriter(tmp_path / "out.txt")

    assert writer.__exit__(ValueError, ValueError("boom"), None) is False

    assert not (tmp_path / "out.txt").exists()


def test_safe_file_writer_second_exit_does_nothing(tmp_path: Path) -> None:
    """The state is reset after the first `__exit__`; a repeated one cannot commit again."""
    target = tmp_path / "out.txt"
    writer = SafeFileWriter(target)
    with writer as handle:
        handle.write("new")

    assert writer.__exit__(None, None, None) is False

    assert target.read_text(encoding="utf-8") == "new"
    assert _drafts(tmp_path) == []


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")
def test_safe_file_writer_keeps_the_mode_of_the_replaced_file(tmp_path: Path) -> None:
    """A 0o600 file stays 0o600 after being replaced."""
    target = tmp_path / "secret.txt"
    target.write_text("old", encoding="utf-8")
    os.chmod(target, 0o600)

    with SafeFileWriter(target) as handle:
        handle.write("new")

    assert stat.S_IMODE(target.stat().st_mode) == 0o600


def test_safe_file_writer_writes_through_a_symlink_and_keeps_the_link(tmp_path: Path) -> None:
    """The link is resolved: the real file is replaced, the link stays a link."""
    real = tmp_path / "real.txt"
    real.write_text("old", encoding="utf-8")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(real)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available here")

    with SafeFileWriter(link) as handle:
        handle.write("new")

    assert link.is_symlink()
    assert real.read_text(encoding="utf-8") == "new"


# ----------------------------------------------------------------------
# Append
# ----------------------------------------------------------------------

def test_safe_file_writer_append_continues_after_existing_text(tmp_path: Path) -> None:
    """Append copies the old content into the draft and continues after it."""
    target = tmp_path / "log.txt"
    target.write_bytes(b"one\n")

    with SafeFileWriter(target, mode="a") as handle:
        handle.write("two\n")

    assert target.read_bytes() == b"one\ntwo\n"
    assert _drafts(tmp_path) == []


def test_safe_file_writer_append_binary(tmp_path: Path) -> None:
    """Binary append works the same way."""
    target = tmp_path / "log.bin"
    target.write_bytes(b"\x01\x02")

    with SafeFileWriter(target, mode="ab") as handle:
        handle.write(b"\x03")

    assert target.read_bytes() == b"\x01\x02\x03"


@pytest.mark.parametrize("mode, data", [("a", "x"), ("ab", b"x")])
def test_safe_file_writer_append_creates_a_missing_file(tmp_path: Path, mode, data) -> None:
    """Appending to nothing is writing."""
    target = tmp_path / "log.txt"

    with SafeFileWriter(target, mode=mode) as handle:
        handle.write(data)

    assert target.read_bytes() == b"x"


def test_safe_file_writer_failed_append_keeps_original(tmp_path: Path) -> None:
    """An exception during append leaves the old content untouched."""
    target = tmp_path / "log.txt"
    target.write_bytes(b"one\n")

    with pytest.raises(ValueError):
        with SafeFileWriter(target, mode="a") as handle:
            handle.write("half")
            raise ValueError("boom")

    assert target.read_bytes() == b"one\n"
    assert _drafts(tmp_path) == []


def test_safe_file_writer_append_twice_with_utf8_sig_writes_one_bom_only(tmp_path: Path) -> None:
    """The text wrapper knows the draft already has content and writes no second BOM."""
    target = tmp_path / "bom.txt"

    with SafeFileWriter(target, encoding="utf-8-sig") as handle:
        handle.write("a")
    with SafeFileWriter(target, mode="a", encoding="utf-8-sig") as handle:
        handle.write("b")

    assert target.read_bytes() == b"\xef\xbb\xbfab"


# ----------------------------------------------------------------------
# Text options
# ----------------------------------------------------------------------

@pytest.mark.parametrize(
    "newline, expected",
    [
        ("\n", b"a\nb\n"),
        ("\r\n", b"a\r\nb\r\n"),
        ("\r", b"a\rb\r"),
        (None, ("a" + os.linesep + "b" + os.linesep).encode("ascii")),
    ],
    ids=["LF", "CRLF", "CR", "platform"],
)
def test_safe_file_writer_newline_decides_the_line_ending(tmp_path: Path, newline, expected) -> None:
    """Every "\\n" in the text becomes the chosen ending."""
    target = tmp_path / "out.txt"

    with SafeFileWriter(target, newline=newline) as handle:
        handle.write("a\nb\n")

    assert target.read_bytes() == expected


def test_safe_file_writer_default_newline_is_lf_on_every_platform(tmp_path: Path) -> None:
    """The same program produces the same bytes on every machine."""
    target = tmp_path / "out.txt"

    with SafeFileWriter(target) as handle:
        handle.write("a\nb\n")

    assert target.read_bytes() == b"a\nb\n"


def test_safe_file_writer_uses_the_requested_encoding(tmp_path: Path) -> None:
    """The text is encoded with the given encoding."""
    target = tmp_path / "out.txt"

    with SafeFileWriter(target, encoding="cp1250") as handle:
        handle.write("žluťoučký")

    assert target.read_bytes() == "žluťoučký".encode("cp1250")


def test_safe_file_writer_errors_replace_writes_a_substitute(tmp_path: Path) -> None:
    """errors="replace" writes a substitute instead of failing."""
    target = tmp_path / "out.txt"

    with SafeFileWriter(target, encoding="ascii", errors="replace") as handle:
        handle.write("é")

    assert target.read_bytes() == b"?"


def test_safe_file_writer_unencodable_character_keeps_original(tmp_path: Path) -> None:
    """With errors="strict" the failure propagates and the original survives."""
    target = tmp_path / "out.txt"
    target.write_text("old", encoding="utf-8")

    with pytest.raises(UnicodeEncodeError):
        with SafeFileWriter(target, encoding="ascii") as handle:
            handle.write("é")

    assert target.read_text(encoding="utf-8") == "old"
    assert _drafts(tmp_path) == []


# ----------------------------------------------------------------------
# Failure cards
# ----------------------------------------------------------------------

@pytest.mark.parametrize(
    "mode, operation",
    [("w", "WRITE"), ("wb", "WRITE"), ("a", "APPEND"), ("ab", "APPEND")],
)
def test_safe_file_writer_directory_at_target_is_state_error(tmp_path: Path, mode, operation) -> None:
    """A directory can never be replaced by a file; nothing is created."""
    target = tmp_path / "folder"
    target.mkdir()

    with pytest.raises(StateError) as info:
        with SafeFileWriter(target, mode=mode):
            pass

    assert info.value.error_name == f"FILE_{operation}_DESTINATION_IS_DIRECTORY"
    assert isinstance(info.value, IsADirectoryError)
    assert target.is_dir()
    assert _drafts(tmp_path) == []


def test_safe_file_writer_draft_create_failure_is_access_error(tmp_path: Path, monkeypatch) -> None:
    """No room for a draft: AccessError, the target is untouched."""
    target = tmp_path / "out.txt"
    target.write_text("old", encoding="utf-8")

    def refusing_create_draft(target_path, *, append):
        raise PermissionError("denied")

    monkeypatch.setattr(MODULE, "create_draft", refusing_create_draft)

    with pytest.raises(AccessError) as info:
        with SafeFileWriter(target) as handle:
            handle.write("new")

    assert info.value.error_name == "SAFE_WRITER_DRAFT_CREATE_FAILED"
    assert isinstance(info.value, PermissionError)
    assert target.read_text(encoding="utf-8") == "old"


def test_safe_file_writer_draft_open_failure_removes_the_draft(tmp_path: Path, monkeypatch) -> None:
    """The old writer leaked the just-created draft; now it is deleted before the card is raised."""
    target = tmp_path / "out.txt"
    target.write_text("old", encoding="utf-8")
    original_open = Path.open

    def refusing_open(self, *args, **kwargs):
        if self.name.endswith(".draft"):
            raise PermissionError("denied")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", refusing_open)

    with pytest.raises(AccessError) as info:
        with SafeFileWriter(target) as handle:
            handle.write("new")

    assert info.value.error_name == "SAFE_WRITER_DRAFT_OPEN_FAILED"
    assert isinstance(info.value, PermissionError)
    assert _drafts(tmp_path) == []
    assert target.read_text(encoding="utf-8") == "old"


@pytest.mark.parametrize("mode, operation", [("w", "WRITE"), ("a", "APPEND")])
def test_safe_file_writer_close_failure_is_access_error(tmp_path: Path, monkeypatch, mode, operation) -> None:
    """A full disk shows up at close: the data never fully arrived, so the draft is discarded and reported."""
    target = tmp_path / "out.txt"
    target.write_text("old", encoding="utf-8")
    monkeypatch.setattr(SafeFileWriter, "_open_draft", lambda self: _FailingHandle())

    with pytest.raises(AccessError) as info:
        with SafeFileWriter(target, mode=mode) as handle:
            handle.write("new")

    assert info.value.error_name == f"FILE_{operation}_FAILED"
    assert isinstance(info.value, OSError)
    assert target.read_text(encoding="utf-8") == "old"
    assert _drafts(tmp_path) == []


def test_safe_file_writer_close_failure_does_not_mask_the_error_of_the_block(tmp_path: Path, monkeypatch) -> None:
    """The old __exit__ let the close error hide the real one; now the block's exception wins."""
    target = tmp_path / "out.txt"
    target.write_text("old", encoding="utf-8")
    monkeypatch.setattr(SafeFileWriter, "_open_draft", lambda self: _FailingHandle())

    with pytest.raises(ValueError, match="real problem"):
        with SafeFileWriter(target) as handle:
            handle.write("new")
            raise ValueError("real problem")

    assert target.read_text(encoding="utf-8") == "old"
    assert _drafts(tmp_path) == []


def test_safe_file_writer_commit_failure_is_access_error(tmp_path: Path, monkeypatch) -> None:
    """A failed swap leaves the original in place and removes the draft."""
    target = tmp_path / "out.txt"
    target.write_text("old", encoding="utf-8")

    def refusing_commit(draft_path, target_path, **kwargs):
        raise PermissionError("locked")

    monkeypatch.setattr(MODULE, "commit_draft", refusing_commit)

    with pytest.raises(AccessError) as info:
        with SafeFileWriter(target) as handle:
            handle.write("new")

    assert info.value.error_name == "SAFE_WRITER_COMMIT_FAILED"
    assert isinstance(info.value, PermissionError)
    assert target.read_text(encoding="utf-8") == "old"
    assert _drafts(tmp_path) == []


@pytest.mark.parametrize("sync", [False, True])
def test_safe_file_writer_forwards_sync_to_the_commit(tmp_path: Path, monkeypatch, sync) -> None:
    """The durability flag reaches commit_draft."""
    original_commit = MODULE.commit_draft
    received: list[bool] = []

    def recording_commit(draft_path, target_path, **kwargs):
        received.append(kwargs["sync"])
        original_commit(draft_path, target_path, **kwargs)

    monkeypatch.setattr(MODULE, "commit_draft", recording_commit)
    target = tmp_path / "out.txt"

    with SafeFileWriter(target, sync=sync) as handle:
        handle.write("x")

    assert received == [sync]
