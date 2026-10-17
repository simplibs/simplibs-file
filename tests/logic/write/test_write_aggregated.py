import os
from pathlib import Path
import pytest
from simplibs.exception import AlreadyExistsError, ConversionError
from simplibs.file.logic.write import write_aggregated


def test_write_aggregated_joins_parts_with_a_newline_by_default(tmp_path: Path) -> None:
    """The exact join: no trailing newline unless asked."""
    target = tmp_path / "out.txt"

    write_aggregated(target, ["one", "two", "three"])

    assert target.read_bytes() == b"one\ntwo\nthree"


@pytest.mark.parametrize(
    "separator, expected",
    [("\n\n", b"a\n\nb\n\nc"), ("\n---\n", b"a\n---\nb\n---\nc"), ("", b"abc"), (", ", b"a, b, c")],
    ids=["blank-line", "rule", "none", "comma"],
)
def test_write_aggregated_uses_the_given_separator(tmp_path: Path, separator, expected) -> None:
    """Any separator, including an empty one."""
    target = tmp_path / "out.txt"

    write_aggregated(target, ["a", "b", "c"], separator=separator)

    assert target.read_bytes() == expected


def test_write_aggregated_trailing_newline_adds_exactly_one(tmp_path: Path) -> None:
    """Opt-in terminator after the last fragment."""
    target = tmp_path / "out.txt"

    write_aggregated(target, ["a", "b"], trailing_newline=True)

    assert target.read_bytes() == b"a\nb\n"


def test_write_aggregated_single_part_has_no_separator(tmp_path: Path) -> None:
    """One fragment is written as it is."""
    target = tmp_path / "out.txt"

    write_aggregated(target, ["only"])

    assert target.read_bytes() == b"only"


def test_write_aggregated_empty_parts_give_an_empty_file(tmp_path: Path) -> None:
    """Nothing to join, nothing to write."""
    target = tmp_path / "out.txt"

    write_aggregated(target, [])

    assert target.read_bytes() == b""


def test_write_aggregated_empty_parts_with_trailing_newline_still_give_an_empty_file(tmp_path: Path) -> None:
    """There is no last fragment to terminate — the same rule as `write_lines`."""
    target = tmp_path / "out.txt"

    write_aggregated(target, [], trailing_newline=True)

    assert target.read_bytes() == b""


def test_write_aggregated_one_empty_part_with_trailing_newline_gives_a_newline(tmp_path: Path) -> None:
    """A collection with an empty fragment is not an empty collection."""
    target = tmp_path / "out.txt"

    write_aggregated(target, [""], trailing_newline=True)

    assert target.read_bytes() == b"\n"


def test_write_aggregated_keeps_blank_and_multiline_parts_as_they_are(tmp_path: Path) -> None:
    """Fragments are arbitrary chunks, not lines."""
    target = tmp_path / "out.txt"

    write_aggregated(target, ["line 1\nline 2", "", "line 3"], separator="\n")

    assert target.read_bytes() == b"line 1\nline 2\n\nline 3"


@pytest.mark.parametrize(
    "newline, expected",
    [
        ("\r\n", b"a\r\nb"),
        (None, ("a" + os.linesep + "b").encode("ascii")),
    ],
    ids=["CRLF", "platform"],
)
def test_write_aggregated_newline_translates_every_lf(tmp_path: Path, newline, expected) -> None:
    """The separator's `\\n` is translated like any other."""
    target = tmp_path / "out.txt"

    write_aggregated(target, ["a", "b"], newline=newline)

    assert target.read_bytes() == expected


def test_write_aggregated_accepts_a_tuple_of_parts(tmp_path: Path) -> None:
    """Any Collection of strings works."""
    target = tmp_path / "out.txt"

    write_aggregated(target, ("a", "b"))

    assert target.read_bytes() == b"a\nb"


def test_write_aggregated_uses_the_given_encoding(tmp_path: Path) -> None:
    """cp1250 produces its own bytes."""
    target = tmp_path / "out.txt"

    write_aggregated(target, ["žluť", "kůň"], encoding="cp1250")

    assert target.read_bytes() == "žluť\nkůň".encode("cp1250")


def test_write_aggregated_returns_the_normalized_path(tmp_path: Path) -> None:
    """The result is the absolute, resolved target."""
    assert write_aggregated(tmp_path / "out.txt", ["a"]) == (tmp_path / "out.txt").resolve()


@pytest.mark.parametrize("use_draft", [True, False])
def test_write_aggregated_overwrite_false_refuses_an_existing_file(tmp_path: Path, use_draft) -> None:
    """The original is untouched."""
    target = tmp_path / "out.txt"
    target.write_text("old", encoding="utf-8")

    with pytest.raises(AlreadyExistsError):
        write_aggregated(target, ["new"], overwrite=False, use_draft=use_draft)

    assert target.read_text(encoding="utf-8") == "old"


def test_write_aggregated_unencodable_character_keeps_the_existing_file(tmp_path: Path) -> None:
    """The text is encoded before the disk is touched."""
    target = tmp_path / "out.txt"
    target.write_text("old", encoding="utf-8")

    with pytest.raises(ConversionError):
        write_aggregated(target, ["abc", "€"], encoding="ascii")

    assert target.read_text(encoding="utf-8") == "old"
