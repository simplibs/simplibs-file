import hashlib
from simplibs.path import PathLike
from simplibs.validate import validate_call
# Outers
from ...annotations import ByteCount, HashAlgorithm
from .._common.helpers import resolve_source_file
from .._common.validations import raise_file_access_error


@validate_call
def file_hash(
    path: PathLike,
    *,
    algorithm: HashAlgorithm = "sha256",
    chunk_size: ByteCount = 1_048_576,
) -> str:
    """Compute the hash of a file's content, reading it in chunks.

    Args:
        path: The file to hash (a symlink is followed).
        algorithm: The hash algorithm. Defaults to `"sha256"`. `"md5"` and
            `"sha1"` are for change detection and checksums, never for security.
        chunk_size: How many bytes to read at a time. Defaults to 1 MiB, so
            a file of any size is hashed with flat memory use.

    Returns:
        The digest as a lowercase hexadecimal string.

    Raises:
        NotFoundError: If the file does not exist.
        StateError: If the path is not a regular file.
        AccessError: If the OS refuses the read.
    """

    # 1. Normalize and verify there is a regular file
    source = resolve_source_file(path, "hash")

    # 2. The two legacy algorithms are marked "not for security", so they also work on FIPS-restricted systems
    legacy = algorithm in ("md5", "sha1")
    digest = hashlib.new(algorithm, usedforsecurity=not legacy)

    # 3. Feed the file chunk by chunk
    try:
        with source.open("rb") as handle:
            while chunk := handle.read(chunk_size):
                digest.update(chunk)
    except OSError as caught_exc:
        raise_file_access_error(source, "hash", caught_exc)

    # 4. The hex digest
    return digest.hexdigest()


_DESIGN_NOTES = """
# file_hash — "Did This File Change?"

## Purpose
Change detection and de-duplication in extraction pipelines: hash a file,
compare with the stored value, skip unchanged work.

## Flat Memory
The file is never loaded whole; 1 MiB chunks keep the footprint constant.

## `usedforsecurity=False` for `md5` and `sha1`
On FIPS-restricted systems `hashlib.md5()` raises unless it is declared
non-security. This library offers those two only for checksums, so declaring it
is honest — and resolves the open question from `HashAlgorithm`.

## Content Only
The path and the metadata are not part of the hash: two identical files in
different folders hash equal.

## No `shake_*`
Variable-length digests need a length; see `HashAlgorithm`.

## TODO(test)
Empty file (known digests); chunk boundary (`chunk_size` smaller and larger than the file); every algorithm
against `hashlib`; the hash of a file changes with one byte.
"""
