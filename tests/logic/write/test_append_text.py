import os
from pathlib import Path
import pytest
from simplibs.exception import ConversionError, StateError
from simplibs.file.logic.write import append_text


def _drafts(folder: Path) -> list[Path]:
    return sorted(folder.glob(".*.draft"))


@pytest.mark.parametrize("use_draft", [True, False])
def test_append_text_creates_a_missing_file(tmp_path: Path, use_draft) -> None:
    """Appending to nothing is writing."""
    target = tmp_path / "log.txt"

    append_text(target, "one\n", use_draft=use_draft)

    assert target.read_bytes() == b"one\n"


@pytest.mark.parametrize("use_draft", [True, False])
def test_append_text_adds_after_the_existing_content(tmp_path: Path, use_draft) -> None:
    """The old content stays, the new text follows."""
    target = tmp_path / "log.txt"
    target.write_text("one\n", encoding="utf-8")

    append_text(target, "two\n", use_draft=use_draft)

    assert target.read_bytes() == b"one\ntwo\n"
    assert _drafts(tmp_path) == []


def test_append_text_several_appends_accumulate(tmp_path: Path) -> None:
    """Every append adds to the end."""
    target = tmp_path / "log.txt"

    for line in ("a\n", "b\n", "c\n"):
        append_text(target, line)

    assert target.read_bytes() == b"a\nb\nc\n"


@pytest.mark.parametrize(
    "newline, expected",
    [("\n", b"a\n"), ("\r\n", b"a\r\n"), ("\r", b"a\r"), (None, ("a" + os.linesep).encode("ascii"))],
    ids=["LF", "CRLF", "CR", "platform"],
)
def test_append_text_newline_decides_the_line_ending(tmp_path: Path, newline, expected) -> None:
    """Every `\\n` becomes the chosen ending."""
    target = tmp_path / "log.txt"

    append_text(target, "a\n", newline=newline)

    assert target.read_bytes() == expected


def test_append_text_uses_the_given_encoding(tmp_path: Path) -> None:
    """cp1250 produces its own bytes."""
    target = tmp_path / "log.txt"

    append_text(target, "žluť", encoding="cp1250")

    assert target.read_bytes() == "žluť".encode("cp1250")


def test_append_text_errors_replace(tmp_path: Path) -> None:
    """errors="replace" writes a substitute instead of failing."""
    target = tmp_path / "log.txt"

    append_text(target, "aéb", encoding="ascii", errors="replace")

    assert target.read_bytes() == b"a?b"


# ----------------------------------------------------------------------
# One BOM per file
# ----------------------------------------------------------------------

@pytest.mark.parametrize("use_draft", [True, False])
def test_append_text_twice_with_utf8_sig_writes_exactly_one_bom(tmp_path: Path, use_draft) -> None:
    """A BOM belongs at the start of a file, never in the middle."""
    target = tmp_path / "log.txt"

    append_text(target, "a", encoding="utf-8-sig", use_draft=use_draft)
    append_text(target, "b", encoding="utf-8-sig", use_draft=use_draft)

    assert target.read_bytes() == b"\xef\xbb\xbfab"


@pytest.mark.parametrize("encoding", ["utf-16", "utf-32"])
def test_append_text_twice_with_a_bom_codec_decodes_cleanly(tmp_path: Path, encoding) -> None:
    """The file decodes as one piece of text, without a BOM in the middle."""
    target = tmp_path / "log.txt"

    append_text(target, "ab", encoding=encoding)
    append_text(target, "cd", encoding=encoding)

    assert target.read_bytes().decode(encoding) == "abcd"


def test_append_text_to_an_empty_existing_file_keeps_the_bom(tmp_path: Path) -> None:
    """An empty file has no content the BOM would land in the middle of."""
    target = tmp_path / "log.txt"
    target.write_bytes(b"")

    append_text(target, "a", encoding="utf-8-sig")

    assert target.read_bytes() == b"\xef\xbb\xbfa"


def test_append_text_to_a_missing_file_with_a_bom_codec_writes_the_bom(tmp_path: Path) -> None:
    """A new file keeps its BOM."""
    target = tmp_path / "log.txt"

    append_text(target, "a", encoding="utf-8-sig")

    assert target.read_bytes() == b"\xef\xbb\xbfa"


# ----------------------------------------------------------------------
# Failures
# ----------------------------------------------------------------------

@pytest.mark.parametrize("use_draft", [True, False])
def test_append_text_unencodable_character_keeps_the_file_untouched(tmp_path: Path, use_draft) -> None:
    """The text is encoded before the disk is touched."""
    target = tmp_path / "log.txt"
    target.write_text("old", encoding="utf-8")

    with pytest.raises(ConversionError) as info:
        append_text(target, "€", encoding="ascii", use_draft=use_draft)

    assert info.value.error_name == "FILE_ENCODE_FAILED"
    assert target.read_text(encoding="utf-8") == "old"
    assert _drafts(tmp_path) == []


def test_append_text_unencodable_character_does_not_create_the_file(tmp_path: Path) -> None:
    """No file appears."""
    target = tmp_path / "log.txt"

    with pytest.raises(ConversionError):
        append_text(target, "€", encoding="ascii")

    assert not target.exists()


def test_append_text_directory_at_target_is_a_state_error(tmp_path: Path) -> None:
    """A directory cannot be appended to."""
    with pytest.raises(StateError) as info:
        append_text(tmp_path, "x")

    assert info.value.error_name == "FILE_APPEND_DESTINATION_IS_DIRECTORY"


def test_append_text_returns_the_normalized_path(tmp_path: Path) -> None:
    """The result is the absolute, resolved target."""
    assert append_text(tmp_path / "log.txt", "x") == (tmp_path / "log.txt").resolve()


def test_append_text_accepts_string_path(tmp_path: Path) -> None:
    """A str path works like a Path."""
    append_text(str(tmp_path / "log.txt"), "x")

    assert (tmp_path / "log.txt").read_text(encoding="utf-8") == "x"
