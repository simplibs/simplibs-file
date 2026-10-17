import pytest
from simplibs.file.annotations._helpers import is_text_encoding


@pytest.mark.parametrize(
    "name",
    ["utf-8", "UTF-8", "utf8", "utf-8-sig", "utf-16", "utf-32", "ascii", "latin-1", "cp1250", "utf-7"],
)
def test_is_text_encoding_accepts_real_text_encodings(name) -> None:
    """A codec that can both encode and decode text is a usable encoding."""
    assert is_text_encoding(name) is True


@pytest.mark.parametrize("name", ["rot13", "base64", "hex", "zlib", "bz2"])
def test_is_text_encoding_rejects_non_text_codecs(name) -> None:
    """Str-to-str and bytes-to-bytes codecs exist in the registry but are not text encodings."""
    assert is_text_encoding(name) is False


@pytest.mark.parametrize("name", ["no-such-encoding", "utf-99", "cp0000"])
def test_is_text_encoding_rejects_unknown_names(name) -> None:
    """An unknown name is a plain False, never a LookupError."""
    assert is_text_encoding(name) is False


@pytest.mark.parametrize("name", ["", " ", "   ", "\t", "\n"])
def test_is_text_encoding_rejects_blank_names(name) -> None:
    """A blank name is never an encoding."""
    assert is_text_encoding(name) is False


@pytest.mark.parametrize("name", [None, 42, 1.5, b"utf-8", ["utf-8"], ("utf-8",)])
def test_is_text_encoding_rejects_non_strings(name) -> None:
    """Only a string can be an encoding name; other types answer False without raising."""
    assert is_text_encoding(name) is False


def test_is_text_encoding_survives_embedded_null_character() -> None:
    """A name with a NUL character must not escape as a ValueError."""
    assert is_text_encoding("utf-8\x00") is False
