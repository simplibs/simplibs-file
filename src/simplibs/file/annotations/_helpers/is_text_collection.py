from collections.abc import Collection


def is_text_collection(value: Collection[str]) -> bool:
    """Check whether a value is a collection of text items — and not a text itself.

    Args:
        value: The candidate.

    Returns:
        True for a sized, re-iterable collection (`list`, `tuple`, `set`, `dict`, ...)
        whose every item is a `str`; False for a bare `str`, for `bytes`-like objects,
        for generators and other one-shot iterables, and for any collection holding a non-`str` item.
    """

    # 1. A text is technically a collection of one-character texts — never what the caller meant
    if isinstance(value, (str, bytes, bytearray)):
        return False

    # 2. A real collection: it has a length and can be walked more than once (not a generator)
    if not isinstance(value, Collection):
        return False

    # 3. Every item is text
    return all(isinstance(item, str) for item in value)


_DESIGN_NOTES = """
# is_text_collection — "Several Texts, Not One Text"

The rule behind `TextCollection`. `"abc"` is a `Collection[str]` in Python (of
the characters `"a"`, `"b"`, `"c"`), so `write_lines(path, "abc")` would write
three lines instead of failing — the classic result of a forgotten list. The
predicate refuses a bare `str` (and `bytes`-like objects) outright.

## Why It Checks the Items Too
The base type of `TextCollection` already says `Collection[str]`, but the
predicate does not rely on how deep a validator looks into it: one pass over the
items makes the rule complete on its own, so `[1, 2]` is refused by the same
function that refuses `"abc"`.

## Why `Collection`
A `Collection` has a length and can be iterated repeatedly, so checking the items
here does not consume what the writer is about to use. A generator is refused —
it would be emptied by the check.
"""
