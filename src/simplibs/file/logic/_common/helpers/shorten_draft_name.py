import os


# The draft name is the target name plus "." + "." + 8 hex characters + ".draft" = 16 characters
_ADDED_LENGTH: int = 16

# The longest file name POSIX filesystems accept, counted in BYTES
_MAX_NAME_BYTES: int = 255

# The longest target-name part kept in a draft name, counted in characters
_MAX_CHARACTERS: int = 100


def shorten_draft_name(name: str) -> str:
    """Shorten a target file name so the draft name built from it stays creatable.

    Args:
        name: The final name of the target file (name and suffix, no folder).

    Returns:
        The name unchanged when it is short enough, otherwise its beginning —
        at most 100 characters and few enough bytes that the draft name
        (`.<result>.<8 hex>.draft`) fits into 255 bytes. Never cuts inside a character.
    """

    # 1. Limit by characters (the Windows limit counts characters)
    short = name[:_MAX_CHARACTERS]

    # 2. Limit by bytes (the Linux and macOS limit counts bytes; one character can take up to four)
    while len(os.fsencode(short)) > _MAX_NAME_BYTES - _ADDED_LENGTH:
        short = short[:-1]

    # 3. The part of the name the draft keeps
    return short


_DESIGN_NOTES = """
# shorten_draft_name — a Draft Name That Fits the Filesystem

## Purpose
`create_draft` builds `.<name>.<8hex>.draft` next to the target. For a very long
target name that would exceed the file-name limit, so the name part is cut.
One question, answered once, out of `create_draft`.

## Characters AND Bytes
Cutting to a fixed number of characters is enough on Windows (the limit counts
UTF-16 characters) but not on Linux and macOS, where the limit is 255 BYTES: a
name of 100 euro signs is 300 bytes. The result is therefore also limited by
`len(os.fsencode(...))`, which is the byte count the filesystem itself sees
(including undecodable bytes preserved as surrogates).

## Whole Characters Only
The loop removes one character at a time, so a multi-byte character is never
split.
"""
