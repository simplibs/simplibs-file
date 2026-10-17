from typing import Literal


HashAlgorithm = Literal[
    "md5",
    "sha1",
    "sha224",
    "sha256",
    "sha384",
    "sha512",
    "sha3_224",
    "sha3_256",
    "sha3_384",
    "sha3_512",
    "blake2b",
    "blake2s",
]
"""A fixed-length hash algorithm guaranteed by `hashlib`.

`md5` and `sha1` are for change detection and checksums only, never for security.
"""


_DESIGN_NOTES = """
# HashAlgorithm — Fixed-Length Algorithms of `hashlib`

## Purpose
The `algorithm=` parameter of `file_hash`.

## Why Not `hashlib.algorithms_guaranteed`
That set contains `shake_128` and `shake_256`, whose digest needs an explicit
length — `hexdigest()` without one raises. They are left out instead of
growing a `length` parameter nobody asked for.
"""
