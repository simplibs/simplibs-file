import pytest
from simplibs.file.annotations._helpers import is_byte_count


@pytest.mark.parametrize("value", [1, 2, 8192, 1_048_576, 10**12])
def test_is_byte_count_accepts_positive_integers(value) -> None:
    """Every int greater than zero is a usable number of bytes."""
    assert is_byte_count(value) is True


@pytest.mark.parametrize("value", [0, -1, -8192])
def test_is_byte_count_rejects_zero_and_negatives(value) -> None:
    """Zero would spin a read loop forever; a negative would read everything."""
    assert is_byte_count(value) is False


@pytest.mark.parametrize("value", [True, False])
def test_is_byte_count_rejects_bool(value) -> None:
    """A bool is an int in Python, but never what the caller meant."""
    assert is_byte_count(value) is False


@pytest.mark.parametrize("value", [1.0, 1.5, "1", b"1", None, [1], (1,), {"a": 1}])
def test_is_byte_count_rejects_other_types(value) -> None:
    """Anything that is not an int is rejected without raising."""
    assert is_byte_count(value) is False
