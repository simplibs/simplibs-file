from collections.abc import Collection
from typing import Annotated
# Inners
from ._helpers import is_text_collection


TextCollection = Annotated[Collection[str], is_text_collection]
"""A collection of texts (lines, fragments). A bare `str`, a generator and any non-`str` item are rejected."""


_DESIGN_NOTES = """
# TextCollection — Many Texts, Never One Text

## Purpose
The type of `lines` (`write_lines`) and `parts` (`write_aggregated`). A plain
`Collection[str]` accepts `"abc"` — a string is a collection of characters — so
a forgotten list would silently become one line per letter. The annotation fails
at the call with the library's usual card instead.

## Why `Annotated`
Same as `ByteCount`: an editor and a type checker see a plain `Collection[str]`,
while `@validate_call` reads the predicate from the metadata and checks the value.

## Collection, Not Iterable
The writers use the items twice (join + emptiness test) and the validation walks
them once more, so a generator would arrive empty. A `Collection` can be
iterated repeatedly.
"""
