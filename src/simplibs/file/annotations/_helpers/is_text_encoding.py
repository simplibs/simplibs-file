def is_text_encoding(name: str) -> bool:
    """Check whether a name is a text encoding Python can both encode and decode with.

    Args:
        name: The candidate encoding name (`"utf-8"`, `"cp1250"`, ...).

    Returns:
        True if `str.encode(name)` and `bytes.decode(name)` both work; False
        for unknown names, blank names and non-text codecs (`"rot13"`,
        `"base64"`, `"hex"`).
    """

    # 1. Only a non-blank string can be an encoding name
    if not isinstance(name, str) or not name.strip():
        return False

    # 2. Probe both directions with empty data — this is what a real read/write will need
    try:
        "".encode(name)
        b"".decode(name)

    # 3. Unknown names, bytes-to-bytes codecs, embedded null characters
    except (LookupError, UnicodeError, ValueError):
        return False

    # 4. Both directions work
    return True


_DESIGN_NOTES = """
# is_text_encoding — "Is This a Real Text Encoding?"

## Purpose
The single rule behind the `EncodingName` annotation.

## Why Not Just `codecs.lookup`
`codecs.lookup("rot13")` and `codecs.lookup("base64")` succeed, but they are
str-to-str / bytes-to-bytes transforms: `"x".encode("rot13")` raises a
`LookupError` only at the moment of the real write — after the draft was
created. Probing `"".encode(name)` and `b"".decode(name)` rejects them up
front and checks both directions the library will ever use.

## No Cache
The interpreter caches codec lookups itself; a second cache here would only
add a hashability trap (an unhashable argument would fail before the type check).
"""
