from typing import Annotated
# Inners
from ._helpers import is_byte_count


ByteCount = Annotated[int, is_byte_count]
"""A positive number of bytes (a read chunk, a sample size). Zero, negatives and `bool` are rejected."""


_DESIGN_NOTES = """
# ByteCount — a Size That Cannot Be Zero

## Purpose
The type of `chunk_size` (`file_hash`) and `sample_size` (`is_text_file`).
A read loop with a zero chunk never ends; a negative sample silently reads
everything. The annotation fails at the call with the library's usual card.

## Why `Annotated`
`Annotated[int, is_byte_count]` is a type an editor and a type checker
understand: they see a plain `int` and offer its methods and hints, while
`@validate_call` reads the predicate from the metadata and checks the value.
`validated_type(int, is_byte_count)` builds the same thing, but as a function
call — the result is a value, not a type, so editors cannot follow it. It is
meant for building many such types in bulk, not for a hand-written definition.
"""
