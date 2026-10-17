import pytest
from simplibs.file.annotations._helpers import is_text_collection


@pytest.mark.parametrize(
    "value",
    [[], ["a"], ["a", "b"], ("a", "b"), {"a", "b"}, frozenset({"a"}), {"a": 1}, ["", "č", "Příliš"]],
)
def test_is_text_collection_accepts_collections_of_texts(value) -> None:
    """Any sized, re-iterable collection of `str` is fine — an empty one too."""
    assert is_text_collection(value) is True


@pytest.mark.parametrize("value", ["abc", "", "a", b"abc", bytearray(b"abc")])
def test_is_text_collection_rejects_a_bare_text(value) -> None:
    """A text is a collection of characters in Python — and a forgotten list in practice."""
    assert is_text_collection(value) is False


@pytest.mark.parametrize("value", [[1, 2], ["a", 1], ["a", None], [b"a"], [["a"]], (1,)])
def test_is_text_collection_rejects_non_text_items(value) -> None:
    """One item that is not a `str` is enough to refuse the whole collection."""
    assert is_text_collection(value) is False


def test_is_text_collection_rejects_one_shot_iterables() -> None:
    """A generator or an iterator would be emptied by the check itself."""
    assert is_text_collection(item for item in ["a", "b"]) is False
    assert is_text_collection(iter(["a", "b"])) is False


@pytest.mark.parametrize("value", [None, 5, 1.5, True, object()])
def test_is_text_collection_rejects_non_collections(value) -> None:
    """Anything that is not a collection is refused without raising."""
    assert is_text_collection(value) is False


def test_is_text_collection_does_not_consume_the_collection() -> None:
    """The check walks the items but leaves them as they were."""
    lines = ["a", "b"]
    assert is_text_collection(lines) is True
    assert lines == ["a", "b"]
