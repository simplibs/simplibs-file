from pathlib import Path
import pytest
from simplibs.exception import ConversionError
from simplibs.file.logic.read._helpers import decode_bytes

SOURCE = Path("data/file.txt")


def test_decode_bytes_default_removes_a_bom() -> None:
    """The default `utf-8-sig` strips a BOM written by Windows tools."""
    assert decode_bytes(b"\xef\xbb\xbfhello", SOURCE) == "hello"


def test_decode_bytes_default_accepts_text_without_bom() -> None:
    """`utf-8-sig` also accepts files that have no BOM."""
    assert decode_bytes("žluťoučký".encode("utf-8"), SOURCE) == "žluťoučký"


def test_decode_bytes_plain_utf8_keeps_the_bom_as_a_character() -> None:
    """With plain `utf-8` the BOM is a stray character — that is why the default differs."""
    assert decode_bytes(b"\xef\xbb\xbfhello", SOURCE, encoding="utf-8") == "\ufeffhello"


@pytest.mark.parametrize("encoding", ["cp1250", "latin-1", "utf-16", "utf-32"])
def test_decode_bytes_uses_the_given_encoding(encoding) -> None:
    """Any text encoding works."""
    text = "abc" if encoding == "latin-1" else "žluťoučký"
    assert decode_bytes(text.encode(encoding), SOURCE, encoding=encoding) == text


def test_decode_bytes_leaves_line_endings_untouched() -> None:
    """Decoding changes no characters — newlines are the caller's business."""
    assert decode_bytes(b"a\r\nb\rc\nd", SOURCE) == "a\r\nb\rc\nd"


def test_decode_bytes_empty_data_is_empty_text() -> None:
    """Nothing in, nothing out."""
    assert decode_bytes(b"", SOURCE) == ""


def test_decode_bytes_errors_replace_substitutes_invalid_bytes() -> None:
    """errors="replace" reads what it can instead of failing."""
    assert decode_bytes(b"a\xffb", SOURCE, errors="replace") == "a\ufffdb"


def test_decode_bytes_errors_ignore_drops_invalid_bytes() -> None:
    """errors="ignore" silently drops them."""
    assert decode_bytes(b"a\xffb", SOURCE, errors="ignore") == "ab"


def test_decode_bytes_invalid_bytes_raise_a_card_with_the_offset() -> None:
    """A bare UnicodeDecodeError (a ValueError, invisible to `except OSError`) becomes a card."""
    with pytest.raises(ConversionError) as info:
        decode_bytes(b"ab\xffcd", SOURCE)

    assert info.value.error_name == "FILE_DECODE_FAILED"
    assert isinstance(info.value, UnicodeDecodeError)
    assert "byte offset 2" in str(info.value)
    assert str(SOURCE) in str(info.value)


def test_decode_bytes_utf8_data_with_wrong_encoding_is_a_card() -> None:
    """cp1250 bytes read as UTF-8 fail with a card naming the encoding."""
    with pytest.raises(ConversionError) as info:
        decode_bytes("žluť".encode("cp1250"), SOURCE, encoding="utf-8")

    assert "utf-8" in str(info.value)
