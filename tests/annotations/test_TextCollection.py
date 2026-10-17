from collections.abc import Collection
from typing import Annotated, get_args, get_origin
import pytest
from simplibs.rules import IsTyping
from simplibs.validate.testing import assert_type_contract
from simplibs.file.annotations import TextCollection
from simplibs.file.annotations._helpers import is_text_collection


@pytest.mark.parametrize("value", [[], ["a"], ["a", "b"], ("a", "b"), {"a", "b"}, ["Příliš", "žluťoučký"]])
def test_text_collection_accepts_collections_of_texts(value) -> None:
    """A list, tuple or set of strings — an empty one included — is a collection of texts."""
    assert IsTyping(TextCollection).is_valid(value)


@pytest.mark.parametrize("value", ["abc", "", b"abc", [1, 2], ["a", 1], None, 5, (c for c in "abc")])
def test_text_collection_rejects_everything_else(value) -> None:
    """A bare string, non-text items, a generator and non-collections are rejected."""
    assert not IsTyping(TextCollection).is_valid(value)


def test_text_collection_contract(subtests) -> None:
    """Verify TextCollection satisfies both the Rule contract and @validate_call integration.

    A collection with a wrong item (`[1, 2]`) is deliberately not listed here: the failure card
    names the offending ITEM (`1`), while the contract expects the whole value back. Those cases
    are covered by `test_text_collection_rejects_everything_else`.
    """
    assert_type_contract(
        subtests,
        type_=TextCollection,
        valid_values=[[], ["a", "b"], ("a",), {"a"}],
        invalid_values=["abc", "", None, 5],
        verbose=False,
    )


def test_text_collection_is_an_annotated_collection_of_str() -> None:
    """Spelled as `Annotated`, so editors and type checkers see a plain `Collection[str]` with a predicate attached."""
    assert get_origin(TextCollection) is Annotated
    assert get_args(TextCollection) == (Collection[str], is_text_collection)