import os
from pathlib import Path
import pytest
from simplibs.exception import AlreadyExistsError, ConversionError
from simplibs.file.logic.read import read_text
from simplibs.file.logic.write import write_text


def _drafts(folder: Path) -> list[Path]:
    return sorted(folder.glob(".*.draft"))


@pytest.mark.parametrize("use_draft", [True, False])
def test_write_text_writes_utf8_without_bom_and_with_lf(tmp_path: Path, use_draft) -> None:
    """The defaults: utf-8, no BOM, `\\n` on every platform."""
    target = tmp_path / "out.txt"

    write_text(target, "žluť\nkůň\n", use_draft=use_draft)

    assert target.read_bytes() == "žluť\nkůň\n".encode("utf-8")
    assert _drafts(tmp_path) == []


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
def test_write_text_newline_decides_the_line_ending(tmp_path: Path, newline, expected) -> None:
    """Every `\\n` becomes the chosen ending — the platform no longer decides."""
    target = tmp_path / "out.txt"

    write_text(target, "a\nb\n", newline=newline)

    assert target.read_bytes() == expected


def test_write_text_uses_the_given_encoding(tmp_path: Path) -> None:
    """cp1250 produces its own bytes."""
    target = tmp_path / "out.txt"

    write_text(target, "žluťoučký", encoding="cp1250")

    assert target.read_bytes() == "žluťoučký".encode("cp1250")


def test_write_text_utf8_sig_writes_the_bom_at_the_start(tmp_path: Path) -> None:
    """That is what the encoding means."""
    target = tmp_path / "out.txt"

    write_text(target, "a", encoding="utf-8-sig")

    assert target.read_bytes() == b"\xef\xbb\xbfa"


def test_write_text_errors_replace_writes_a_substitute(tmp_path: Path) -> None:
    """errors="replace" writes a substitute instead of failing."""
    target = tmp_path / "out.txt"

    write_text(target, "aéb", encoding="ascii", errors="replace")

    assert target.read_bytes() == b"a?b"


@pytest.mark.parametrize("use_draft", [True, False])
def test_write_text_empty_text_creates_an_empty_file(tmp_path: Path, use_draft) -> None:
    """An empty write is still a write."""
    target = tmp_path / "empty.txt"

    write_text(target, "", use_draft=use_draft)

    assert target.read_bytes() == b""


def test_write_text_returns_the_normalized_path(tmp_path: Path) -> None:
    """The result is the absolute, resolved target."""
    assert write_text(tmp_path / "out.txt", "x") == (tmp_path / "out.txt").resolve()


def test_write_text_creates_missing_folders(tmp_path: Path) -> None:
    """The target's folder is guaranteed."""
    target = tmp_path / "a" / "b" / "out.txt"

    write_text(target, "x")

    assert target.read_text(encoding="utf-8") == "x"


def test_write_text_round_trip_with_read_text(tmp_path: Path) -> None:
    """What write_text writes, read_text reads back."""
    target = tmp_path / "out.txt"
    text = "žluťoučký kůň\núpěl\n\nďábelské ódy\n"

    write_text(target, text)

    assert read_text(target) == text


def test_write_text_sync_writes_normally(tmp_path: Path) -> None:
    """sync only adds durability."""
    target = tmp_path / "out.txt"

    write_text(target, "x", sync=True)

    assert target.read_text(encoding="utf-8") == "x"


# ----------------------------------------------------------------------
# Failures
# ----------------------------------------------------------------------

@pytest.mark.parametrize("use_draft", [True, False])
def test_write_text_unencodable_character_keeps_the_existing_file(tmp_path: Path, use_draft) -> None:
    """The text is encoded BEFORE the disk is touched — the old `Path.write_text` truncated first."""
    target = tmp_path / "out.txt"
    target.write_text("old", encoding="utf-8")

    with pytest.raises(ConversionError) as info:
        write_text(target, "abc€", encoding="ascii", use_draft=use_draft)

    assert info.value.error_name == "FILE_ENCODE_FAILED"
    assert isinstance(info.value, UnicodeEncodeError)
    assert target.read_text(encoding="utf-8") == "old"
    assert _drafts(tmp_path) == []


def test_write_text_unencodable_character_does_not_create_the_file(tmp_path: Path) -> None:
    """No half-written file appears."""
    target = tmp_path / "out.txt"

    with pytest.raises(ConversionError):
        write_text(target, "€", encoding="ascii")

    assert not target.exists()


@pytest.mark.parametrize("use_draft", [True, False])
def test_write_text_overwrite_false_refuses_an_existing_file(tmp_path: Path, use_draft) -> None:
    """The original is untouched."""
    target = tmp_path / "out.txt"
    target.write_text("old", encoding="utf-8")

    with pytest.raises(AlreadyExistsError):
        write_text(target, "new", overwrite=False, use_draft=use_draft)

    assert target.read_text(encoding="utf-8") == "old"
