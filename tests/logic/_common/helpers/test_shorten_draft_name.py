import os
import pytest
from simplibs.file.logic._common.helpers.shorten_draft_name import shorten_draft_name

_DRAFT_EXTRA = len(".") + len(".") + 8 + len(".draft")


# ----------------------------------------------------------------------
# Names that stay as they are
# ----------------------------------------------------------------------

@pytest.mark.parametrize("name", ["a.txt", "report_20260101.txt", "žluťoučký.txt", "no_suffix", "x" * 100])
def test_shorten_draft_name_keeps_a_short_name(name: str) -> None:
    """A name within both limits is returned unchanged."""
    assert shorten_draft_name(name) == name


def test_shorten_draft_name_keeps_a_name_of_exactly_100_ascii_characters() -> None:
    """The character limit is inclusive."""
    name = "a" * 100

    assert shorten_draft_name(name) == name


# ----------------------------------------------------------------------
# Names that are cut
# ----------------------------------------------------------------------

def test_shorten_draft_name_cuts_a_long_ascii_name_to_100_characters() -> None:
    """The character limit applies first."""
    name = "a" * 300 + ".txt"

    assert shorten_draft_name(name) == "a" * 100


@pytest.mark.parametrize(
    "character, expected_length",
    [("€", 79), ("😀", 59)],
    ids=["three-byte", "four-byte"],
)
def test_shorten_draft_name_respects_the_byte_limit_for_multibyte_characters(character, expected_length) -> None:
    """100 characters can be 300 or 400 bytes — the cut must also fit 255 bytes with the draft's additions."""
    name = character * 100

    short = shorten_draft_name(name)

    assert len(short) == expected_length
    assert name.startswith(short)
    assert len(os.fsencode(short)) + _DRAFT_EXTRA <= 255
    assert len(os.fsencode(short + character)) + _DRAFT_EXTRA > 255


def test_shorten_draft_name_never_splits_a_character() -> None:
    """The result is made of whole characters, so it always encodes and decodes cleanly."""
    short = shorten_draft_name("é€😀" * 60)

    assert os.fsencode(short).decode("utf-8") == short


def test_shorten_draft_name_empty_name_stays_empty() -> None:
    """Nothing to cut."""
    assert shorten_draft_name("") == ""
