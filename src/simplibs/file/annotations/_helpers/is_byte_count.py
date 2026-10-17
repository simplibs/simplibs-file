def is_byte_count(value: int) -> bool:
    """Check whether a value is a usable number of bytes.

    Args:
        value: The candidate.

    Returns:
        True for an `int` greater than zero; False for zero, negatives and `bool`.
    """

    # 1. A real integer (a bool is an int in Python, but never what the caller meant)
    if not isinstance(value, int) or isinstance(value, bool):
        return False

    # 2. At least one byte
    return value > 0


_DESIGN_NOTES = """
# is_byte_count — "A Positive Number of Bytes"

The rule behind `ByteCount`. `chunk_size=0` would make a read loop spin
forever, `sample_size=-1` would read the whole file; both are stopped at the
signature instead.
"""
