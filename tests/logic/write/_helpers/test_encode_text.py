import os
from pathlib import Path
import pytest
from simplibs.exception import ConversionError
from simplibs.file.logic.write._helpers import encode_text

TARGET = Path("out/file.txt")


def test_encode_text_default_is_utf8_without_bom() -> None:
    """The write side stays BOM-free utf-8."""
    assert encode_text("žluť", TARGET) == "žluť".encode("utf-8")


def test_encode_text_returns_bytes() -> None:
    """The result is plain bytes, ready for the core writers."""
    assert type(encode_text("a", TARGET)) is bytes


def test_encode_text_empty_text_is_empty_bytes() -> None:
    """Nothing in, nothing out (for an encoding without a preamble)."""
    assert encode_text("", TARGET) == b""


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
def test_encode_text_newline_replaces_every_lf(newline, expected) -> None:
    """The line ending is applied BEFORE encoding."""
    assert encode_text("a\nb\n", TARGET, newline=newline) == expected


def test_encode_text_lf_default_leaves_text_alone() -> None:
    """No translation when the ending is already `\\n`."""
    assert encode_text("a\nb", TARGET) == b"a\nb"


def test_encode_text_existing_crlf_is_not_recognized_like_open() -> None:
    """Documented: `newline="\\r\\n"` turns `a\\r\\nb` into `a\\r\\r\\nb`, exactly like `open()`."""
    assert encode_text("a\r\nb", TARGET, newline="\r\n") == b"a\r\r\nb"


def test_encode_text_existing_crlf_is_kept_with_the_lf_default() -> None:
    """With the default `\\n` nothing is touched, so own endings survive."""
    assert encode_text("a\r\nb", TARGET) == b"a\r\nb"


def test_encode_text_uses_the_given_encoding() -> None:
    """cp1250 produces its own bytes."""
    assert encode_text("žluťoučký", TARGET, encoding="cp1250") == "žluťoučký".encode("cp1250")


@pytest.mark.parametrize(
    "encoding, bom",
    [("utf-8-sig", b"\xef\xbb\xbf"), ("utf-16", "".encode("utf-16")), ("utf-32", "".encode("utf-32"))],
)
def test_encode_text_bom_codecs_put_a_bom_in_front(encoding, bom) -> None:
    """BOM codecs emit the BOM on every encode call (append handles that elsewhere)."""
    assert encode_text("a", TARGET, encoding=encoding).startswith(bom)


@pytest.mark.parametrize(
    "errors, expected",
    [("replace", b"a?b"), ("ignore", b"ab"), ("backslashreplace", b"a\\xe9b")],
)
def test_encode_text_errors_handlers(errors, expected) -> None:
    """The error handler decides what an unencodable character becomes."""
    assert encode_text("aéb", TARGET, encoding="ascii", errors=errors) == expected


def test_encode_text_unencodable_character_raises_a_card() -> None:
    """A UnicodeEncodeError (a ValueError) becomes a ConversionError naming the character."""
    with pytest.raises(ConversionError) as info:
        encode_text("abc€", TARGET, encoding="ascii")

    assert info.value.error_name == "FILE_ENCODE_FAILED"
    assert isinstance(info.value, UnicodeEncodeError)
    assert "U+20AC" in str(info.value)
    assert str(TARGET) in str(info.value)


def test_encode_text_translates_line_endings_before_encoding() -> None:
    """Position in the failure card refers to the text AFTER translation."""
    with pytest.raises(ConversionError):
        encode_text("a\n€", TARGET, encoding="ascii", newline="\r\n")
