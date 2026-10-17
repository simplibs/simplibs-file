import codecs
from typing import get_args
import pytest
from simplibs.rules import IsTyping
from simplibs.file.annotations import EncodingErrors


@pytest.mark.parametrize(
    "value",
    ["strict", "ignore", "replace", "backslashreplace", "surrogateescape", "surrogatepass"],
)
def test_encoding_errors_accepts_two_way_handlers(value) -> None:
    """Every handler that works both for encoding and decoding is listed."""
    assert IsTyping(EncodingErrors).is_valid(value)


@pytest.mark.parametrize(
    "value",
    ["xmlcharrefreplace", "namereplace", "ignroe", "STRICT", "", None, 1],
)
def test_encoding_errors_rejects_everything_else(value) -> None:
    """Encode-only handlers, typos, wrong case and non-strings are rejected."""
    assert not IsTyping(EncodingErrors).is_valid(value)


@pytest.mark.parametrize("handler", get_args(EncodingErrors))
def test_encoding_errors_handlers_are_registered_in_python(handler) -> None:
    """Every listed handler really exists in the codec registry."""
    assert codecs.lookup_error(handler) is not None


def test_encoding_errors_lists_no_encode_only_handler() -> None:
    """xmlcharrefreplace and namereplace would raise a bare TypeError while decoding."""
    assert not {"xmlcharrefreplace", "namereplace"} & set(get_args(EncodingErrors))
