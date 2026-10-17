from pathlib import Path
from typing import NoReturn
from simplibs.exception import ConversionError


def raise_encode_error(
    path: Path,
    encoding: str,
    caught_exc: UnicodeEncodeError,
) -> NoReturn:
    """Raise ConversionError when text contains a character the encoding cannot represent.

    Args:
        path: The file that was going to be written.
        encoding: The encoding the text was encoded with.
        caught_exc: The `UnicodeEncodeError` that was caught.
    """

    # 1. Name the offending character
    character = caught_exc.object[caught_exc.start]

    # 2. Raise structured ConversionError wrapping the UnicodeEncodeError
    raise ConversionError(
        error_name="FILE_ENCODE_FAILED",
        label=f"text for '{path}'",
        value=str(path),
        problem=(
            f"Cannot encode the text for '{path}' as {encoding!r}.",
            f"Character {character!r} (U+{ord(character):04X}) at position {caught_exc.start} has no representation.",
        ),
        expected=f"Text made only of characters that {encoding!r} can represent.",
        how_to_fix=(
            "Use a wider encoding such as 'utf-8'.",
            "Use errors='replace' or 'backslashreplace' to write a substitute instead of failing.",
        ),
        exception=UnicodeEncodeError,
    )


_DESIGN_NOTES = """
# raise_encode_error — a Character the Encoding Cannot Hold

## Purpose
The write-side twin of `raise_decode_error`. Because the text is encoded to
bytes in memory BEFORE the disk is touched, this card is raised while the
target file is still completely untouched.
"""
