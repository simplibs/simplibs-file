from typing import Literal


EncodingErrors = Literal[
    "strict",
    "ignore",
    "replace",
    "backslashreplace",
    "surrogateescape",
    "surrogatepass",
]
"""How to treat characters or bytes that do not fit the encoding.

Only handlers that work in BOTH directions (encoding and decoding) are listed.
"""


_DESIGN_NOTES = """
# EncodingErrors — the Error Handlers That Work Both Ways

## Purpose
The `errors=` parameter of every text read and write.

## Why Not All Handlers
`xmlcharrefreplace` and `namereplace` are encode-only: used while decoding they
raise a bare `TypeError` from inside the codec machinery. One literal shared by
reads and writes must contain only handlers that are safe for both.

## Why Not a Free `str`
A typo (`"ignroe"`) would only fail when a bad character is finally met —
possibly months later. The literal fails immediately.
"""
