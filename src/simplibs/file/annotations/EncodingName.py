from typing import Annotated
# Inners
from ._helpers import is_text_encoding


EncodingName = Annotated[str, is_text_encoding]
"""The name of a text encoding Python can both encode and decode with.

Rejects unknown names and non-text codecs (`"rot13"`, `"base64"`) before any
file is touched. A rejected value raises `ValidationError` from
`@validate_call`.
"""


_DESIGN_NOTES = """
# EncodingName — a Checked Encoding Name

## Purpose
Without it an unknown encoding surfaces as a bare `LookupError` in the middle
of a read or write. With it, the call fails at the signature, with the
library's usual card, before any draft exists.

## Error Type
A rejected name is a `ValidationError` (a wrong *value* of an argument, like a
blank `PathLike`), not a `ParamError`.

## Same Idea as `PathLike`
One named, documented, reusable annotation instead of a repeated
`Annotated[str, is_text_encoding]` in every signature.

## Why `Annotated`
An editor and a type checker see a plain `str` (so string methods and hints
work), while `@validate_call` reads the predicate from the metadata.
`validated_type(str, is_text_encoding)` builds the same thing as a function
call, which an editor cannot see as a type; it is meant for bulk definitions.
"""
