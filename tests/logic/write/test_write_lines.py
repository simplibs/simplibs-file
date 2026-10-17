import os
from pathlib import Path
import pytest
from simplibs.exception import AlreadyExistsError, ConversionError
from simplibs.file.logic.read import read_lines
from simplibs.file.logic.write import write_lines


def test_write_lines_writes_one_line_per_item_with_a_final_newline(tmp_path: Path) -> None:
    """Items carry no ending; the library supplies them, the last line included."""
    target = tmp_path / "out.txt"

    write_lines(target, ["one", "two", "three"])

    assert target.read_bytes() == b"one\ntwo\nthree\n"


def test_write_lines_trailing_newline_false_gives_the_exact_join(tmp_path: Path) -> None:
    """The last line is left unterminated."""
    target = tmp_path / "out.txt"

    write_lines(target, ["one", "two"], trailing_newline=False)

    assert target.read_bytes() == b"one\ntwo"


@pytest.mark.parametrize("trailing_newline", [True, False])
@pytest.mark.parametrize("lines", [[], ()])
def test_write_lines_empty_collection_gives_an_empty_file(tmp_path: Path, lines, trailing_newline) -> None:
    """Never a lone newline."""
    target = tmp_path / "out.txt"

    write_lines(target, lines, trailing_newline=trailing_newline)

    assert target.read_bytes() == b""


def test_write_lines_single_line(tmp_path: Path) -> None:
    """One item, one terminated line."""
    target = tmp_path / "out.txt"

    write_lines(target, ["only"])

    assert target.read_bytes() == b"only\n"


def test_write_lines_accepts_a_tuple(tmp_path: Path) -> None:
    """Any Collection of strings works."""
    target = tmp_path / "out.txt"

    write_lines(target, ("a", "b"))

    assert target.read_bytes() == b"a\nb\n"


def test_write_lines_blank_items_become_blank_lines(tmp_path: Path) -> None:
    """Empty strings are lines too."""
    target = tmp_path / "out.txt"

    write_lines(target, ["a", "", "b"])

    assert target.read_bytes() == b"a\n\nb\n"


@pytest.mark.parametrize(
    "newline, expected",
    [
        ("\r\n", b"a\r\nb\r\n"),
        ("\r", b"a\rb\r"),
        (None, ("a" + os.linesep + "b" + os.linesep).encode("ascii")),
    ],
    ids=["CRLF", "CR", "platform"],
)
def test_write_lines_newline_decides_the_line_ending(tmp_path: Path, newline, expected) -> None:
    """The chosen ending is placed between lines and after the last one."""
    target = tmp_path / "out.txt"

    write_lines(target, ["a", "b"], newline=newline)

    assert target.read_bytes() == expected


def test_write_lines_item_with_its_own_newline_makes_more_lines(tmp_path: Path) -> None:
    """Documented: an item ending in `\\n` gets an empty line after it."""
    target = tmp_path / "out.txt"

    write_lines(target, ["a\n", "b"])

    assert target.read_bytes() == b"a\n\nb\n"


def test_write_lines_uses_the_given_encoding(tmp_path: Path) -> None:
    """cp1250 produces its own bytes."""
    target = tmp_path / "out.txt"

    write_lines(target, ["žluť", "kůň"], encoding="cp1250")

    assert target.read_bytes() == "žluť\nkůň\n".encode("cp1250")


def test_write_lines_round_trip_with_read_lines(tmp_path: Path) -> None:
    """What write_lines writes, read_lines reads back."""
    target = tmp_path / "out.txt"
    lines = ["první", "", "třetí řádek", "čtvrtý"]

    write_lines(target, lines)

    assert read_lines(target) == lines


def test_write_lines_returns_the_normalized_path(tmp_path: Path) -> None:
    """The result is the absolute, resolved target."""
    assert write_lines(tmp_path / "out.txt", ["a"]) == (tmp_path / "out.txt").resolve()


@pytest.mark.parametrize("use_draft", [True, False])
def test_write_lines_overwrite_false_refuses_an_existing_file(tmp_path: Path, use_draft) -> None:
    """The original is untouched."""
    target = tmp_path / "out.txt"
    target.write_text("old", encoding="utf-8")

    with pytest.raises(AlreadyExistsError):
        write_lines(target, ["new"], overwrite=False, use_draft=use_draft)

    assert target.read_text(encoding="utf-8") == "old"


def test_write_lines_unencodable_character_keeps_the_existing_file(tmp_path: Path) -> None:
    """The text is encoded before the disk is touched."""
    target = tmp_path / "out.txt"
    target.write_text("old", encoding="utf-8")

    with pytest.raises(ConversionError):
        write_lines(target, ["abc", "€"], encoding="ascii")

    assert target.read_text(encoding="utf-8") == "old"
