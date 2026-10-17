import pytest
from simplibs.rules import IsTyping
from simplibs.file.annotations import NewlineMode


@pytest.mark.parametrize("value", ["\n", "\r\n", "\r", None])
def test_newline_mode_accepts_line_endings_and_none(value) -> None:
    """The three line endings, or None for the platform's own."""
    assert IsTyping(NewlineMode).is_valid(value)


@pytest.mark.parametrize("value", ["", "\n\r", "\\n", "lf", "crlf", " ", 10, b"\n"])
def test_newline_mode_rejects_everything_else(value) -> None:
    """Empty string, reversed or escaped endings, names and non-strings are rejected."""
    assert not IsTyping(NewlineMode).is_valid(value)
