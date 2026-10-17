from typing import Annotated, get_args, get_origin
import pytest
from simplibs.rules import IsTyping
from simplibs.validate.testing import assert_type_contract
from simplibs.file.annotations import ByteCount
from simplibs.file.annotations._helpers import is_byte_count


@pytest.mark.parametrize("value", [1, 2, 8192, 1_048_576])
def test_byte_count_accepts_positive_integers(value) -> None:
    """A positive int is a usable number of bytes."""
    assert IsTyping(ByteCount).is_valid(value)


@pytest.mark.parametrize("value", [0, -1, True, False, 1.5, "1", None, [1]])
def test_byte_count_rejects_everything_else(value) -> None:
    """Zero, negatives, bool and non-int types are rejected."""
    assert not IsTyping(ByteCount).is_valid(value)


def test_byte_count_contract(subtests) -> None:
    """Verify ByteCount satisfies both the Rule contract and @validate_call integration."""
    assert_type_contract(
        subtests,
        type_=ByteCount,
        valid_values=[1, 8192, 1_048_576],
        invalid_values=[0, -1, True, 1.5, "1", None],
        verbose=False,
    )


def test_byte_count_is_an_annotated_int() -> None:
    """Spelled as `Annotated`, so editors and type checkers see a plain `int` with a predicate attached."""
    assert get_origin(ByteCount) is Annotated
    assert get_args(ByteCount) == (int, is_byte_count)
