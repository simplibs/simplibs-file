from simplibs.validate import validated_type
# Inners
from ._helpers import is_byte_count


ByteCount = validated_type(int, is_byte_count)
"""A positive number of bytes (a read chunk, a sample size). Zero, negatives and `bool` are rejected."""


_DESIGN_NOTES = """
# ByteCount — a Size That Cannot Be Zero

## Purpose
The type of `chunk_size` (`file_hash`) and `sample_size` (`is_text_file`).
A read loop with a zero chunk never ends; a negative sample silently reads
everything. The annotation fails at the call with the library's usual card.
"""
