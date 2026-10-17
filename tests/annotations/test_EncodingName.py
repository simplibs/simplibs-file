import pytest
from simplibs.rules import IsTyping
from simplibs.validate.testing import assert_type_contract
from simplibs.file.annotations import EncodingName


@pytest.mark.parametrize("value", ["utf-8", "utf-8-sig", "utf-16", "ascii", "latin-1", "cp1250"])
def test_encoding_name_accepts_real_text_encodings(value) -> None:
    """A name of a codec that encodes and decodes text is valid."""
    assert IsTyping(EncodingName).is_valid(value)


@pytest.mark.parametrize(
    "value",
    ["", "   ", "rot13", "base64", "hex", "no-such-encoding", None, 42, b"utf-8", ["utf-8"]],
)
def test_encoding_name_rejects_everything_else(value) -> None:
    """Blank names, unknown names, non-text codecs and non-strings are rejected."""
    assert not IsTyping(EncodingName).is_valid(value)


def test_encoding_name_contract(subtests) -> None:
    """Verify EncodingName satisfies both the Rule contract and @validate_call integration."""
    assert_type_contract(
        subtests,
        type_=EncodingName,
        valid_values=["utf-8", "cp1250", "latin-1", "ascii", "utf-16"],
        invalid_values=["", "   ", "rot13", "base64", "no-such-encoding", None, 42],
        verbose=False,
    )
