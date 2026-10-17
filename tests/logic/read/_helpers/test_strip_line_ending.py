import pytest
from simplibs.file.logic.read._helpers import strip_line_ending


@pytest.mark.parametrize(
    "line, expected",
    [
        ("a\n", "a"),
        ("a\r\n", "a"),
        ("a\r", "a"),
        ("\n", ""),
        ("\r\n", ""),
        ("\r", ""),
    ],
)
def test_strip_line_ending_removes_each_of_the_three_endings(line, expected) -> None:
    """`\\n`, `\\r\\n` and `\\r` are all line endings."""
    assert strip_line_ending(line) == expected


@pytest.mark.parametrize("line", ["a", "", "  a  ", "a b"])
def test_strip_line_ending_leaves_a_line_without_ending_unchanged(line) -> None:
    """The last line of a file may have no terminator."""
    assert strip_line_ending(line) == line


@pytest.mark.parametrize(
    "line, expected",
    [
        ("a\n\n", "a\n"),
        ("a\r\r", "a\r"),
        ("a\n\r", "a\n"),
        ("a\r\n\r\n", "a\r\n"),
        ("a\r\n\n", "a\r\n"),
    ],
)
def test_strip_line_ending_removes_exactly_one_ending(line, expected) -> None:
    """Unlike rstrip, only ONE terminator goes — the rest belongs to the line."""
    assert strip_line_ending(line) == expected


def test_strip_line_ending_keeps_surrounding_whitespace() -> None:
    """Only the terminator is removed, never spaces or tabs."""
    assert strip_line_ending("  a \t \n") == "  a \t "


@pytest.mark.parametrize("separator", ["\x0b", "\x0c", "\x1c", "\x85", "\u2028", "\u2029"])
def test_strip_line_ending_ignores_unicode_separators(separator) -> None:
    """Form feeds and Unicode separators are not line endings of this library."""
    line = f"a{separator}"
    assert strip_line_ending(line) == line
