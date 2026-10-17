import pytest
from simplibs.rules import IsTyping
from simplibs.file.annotations import WriterMode


@pytest.mark.parametrize("value", ["w", "wb", "a", "ab"])
def test_writer_mode_accepts_overwrite_and_append_modes(value) -> None:
    """Overwrite or append, text or binary."""
    assert IsTyping(WriterMode).is_valid(value)


@pytest.mark.parametrize(
    "value",
    ["x", "xb", "r", "rb", "r+", "w+", "a+", "wt", "W", "", None, 1],
)
def test_writer_mode_rejects_everything_else(value) -> None:
    """Exclusive creation, in-place update, read modes and non-strings are rejected."""
    assert not IsTyping(WriterMode).is_valid(value)
