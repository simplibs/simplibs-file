from pathlib import Path

import pytest

from simplibs.exception.testing import assert_exception_function
from simplibs.exception import ConversionError
from simplibs.file.logic.write._validations import raise_encode_error


def _encode_error(data: str, encoding: str) -> UnicodeEncodeError:
    """Produce a real UnicodeEncodeError for the given text and encoding."""
    try:
        data.encode(encoding)
    except UnicodeEncodeError as err:
        return err
    raise AssertionError(f"{data!r} unexpectedly encoded as {encoding!r}")


_CASES = [
    ("café", "ascii"),
    ("hello €", "ascii"),
    ("abc😀", "latin-1"),
]


@pytest.mark.parametrize("path", [Path("notes.txt"), Path("data/export.csv")])
@pytest.mark.parametrize("data, encoding", _CASES)
def test_raise_encode_error_contract(subtests, data, encoding, path) -> None:
    """Verify raise_encode_error produces a well-formed ConversionError card."""
    caught_exc = _encode_error(data, encoding)
    character = caught_exc.object[caught_exc.start]

    def raising_wrapper(target_path):
        raise_encode_error(target_path, encoding, caught_exc)

    exc = assert_exception_function(
        subtests,
        raising_wrapper,
        invalid_params=(path,),
        exception_type=ConversionError,
        error_name="FILE_ENCODE_FAILED",
        label=f"text for '{path}'",
        value=str(path),
        problem=(
            f"Cannot encode the text for '{path}' as {encoding!r}.",
            f"Character {character!r} (U+{ord(character):04X}) at position "
            f"{caught_exc.start} has no representation.",
        ),
        expected=f"Text made only of characters that {encoding!r} can represent.",
        how_to_fix=(
            "Use a wider encoding such as 'utf-8'.",
            "Use errors='replace' or 'backslashreplace' to write a substitute instead of failing.",
        ),
        exception=UnicodeEncodeError,
        verbose=False,
    )

    # The card must be catchable as the stdlib type it wraps
    assert isinstance(exc, UnicodeEncodeError)

