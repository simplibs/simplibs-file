from pathlib import Path
import pytest
from simplibs.exception.testing import assert_exception_function
from simplibs.exception import ConversionError
from simplibs.file.logic.read._validations import raise_decode_error


def _decode_error(data: bytes, encoding: str) -> UnicodeDecodeError:
    """Produce a real UnicodeDecodeError for the given bytes and encoding."""
    try:
        data.decode(encoding)
    except UnicodeDecodeError as err:
        return err
    raise AssertionError(f"{data!r} unexpectedly decoded as {encoding!r}")


_CASES = [
    (b"\xff\xfe\x00", "utf-8"),
    (b"abc\xe9", "utf-8"),
    (b"\x00\xd8", "utf-16-le"),
]


@pytest.mark.parametrize("path", [Path("notes.txt"), Path("data/export.csv")])
@pytest.mark.parametrize("data, encoding", _CASES)
def test_raise_decode_error_contract(subtests, data, encoding, path) -> None:
    """Verify raise_decode_error produces a well-formed ConversionError card with the byte offset."""
    caught_exc = _decode_error(data, encoding)

    def raising_wrapper(target_path):
        raise_decode_error(target_path, encoding, caught_exc)

    exc = assert_exception_function(
        subtests,
        raising_wrapper,
        invalid_params=(path,),
        exception_type=ConversionError,
        error_name="FILE_DECODE_FAILED",
        label=f"file '{path}'",
        value=str(path),
        problem=(
            f"Cannot decode '{path}' as {encoding!r}.",
            f"Invalid data at byte offset {caught_exc.start}: {caught_exc.reason}.",
        ),
        expected=f"Content that is valid {encoding!r} text.",
        how_to_fix=(
            "Pass the encoding the file was really written in (e.g. encoding='cp1250' or 'latin-1').",
            "Use errors='replace' to read it with substitution characters instead of failing.",
            "If the file is binary, read it with read_bytes().",
        ),
        exception=UnicodeDecodeError,
        verbose=False,
    )

    # The card must be catchable as the stdlib type it wraps
    assert isinstance(exc, UnicodeDecodeError)


@pytest.mark.parametrize("data, encoding", _CASES)
def test_raise_decode_error_offset_unknown(subtests, data, encoding) -> None:
    """With offset_known=False (streamed read) the card must not print any byte offset."""
    path = Path("stream.txt")
    caught_exc = _decode_error(data, encoding)

    def raising_wrapper(target_path):
        raise_decode_error(target_path, encoding, caught_exc, offset_known=False)

    exc = assert_exception_function(
        subtests,
        raising_wrapper,
        invalid_params=(path,),
        exception_type=ConversionError,
        error_name="FILE_DECODE_FAILED",
        label=f"file '{path}'",
        value=str(path),
        problem=(
            f"Cannot decode '{path}' as {encoding!r}.",
            f"Invalid data found while reading the file: {caught_exc.reason}.",
        ),
        expected=f"Content that is valid {encoding!r} text.",
        verbose=False,
    )

    # A wrong, block-relative offset is worse than none
    assert "byte offset" not in str(exc)
