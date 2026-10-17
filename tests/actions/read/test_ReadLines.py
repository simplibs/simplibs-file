import asyncio
from pathlib import Path
import pytest
from simplibs.actions.testing import assert_action
from simplibs.exception import ConversionError, NotFoundError, StateError, ValidationError
from simplibs.file.actions import ReadLines
from simplibs.path.annotations import PathLike


def test_read_lines_contract(subtests, tmp_path) -> None:
    """Verify the execution and construction contract of the ReadLines action."""
    lf = tmp_path / "lf.txt"
    lf.write_bytes(b"a\nb\n")
    crlf = tmp_path / "crlf.txt"
    crlf.write_bytes(b"x\r\ny")
    empty = tmp_path / "empty.txt"
    empty.write_bytes(b"")
    broken = tmp_path / "broken.txt"
    broken.write_bytes(b"\xff\xfe\xfa")
    assert_action(
        subtests,
        ReadLines(),
        valid_values=[lf, str(crlf), empty],
        expected_outputs=[["a", "b"], ["x", "y"], []],
        invalid_values=[5, "", tmp_path / "missing", tmp_path, broken],
        expected_exception_type=[
            ValidationError,
            ValidationError,
            NotFoundError,
            StateError,
            ConversionError,
        ],
        expected_input_type=PathLike,
        expected_output_type=list[str],
        action_class=ReadLines,
        invalid_init_params=[
            ((), {"encoding": "rot13"}),
            ((), {"encoding": ""}),
            ((), {"errors": "xmlcharrefreplace"}),
            ((), {"errors": "bogus"}),
            ((), {"keep_ends": "x"}),
        ],
        verbose=False,
    )


@pytest.mark.parametrize(
    ("options", "raw", "expected"),
    [
        ({}, b"a\r\nb\rc\nd", ["a", "b", "c", "d"]),
        ({"keep_ends": True}, b"a\r\nb\rc\nd", ["a\r\n", "b\r", "c\n", "d"]),
        ({}, "a\x0cb\u2028c\n".encode("utf-8"), ["a\x0cb\u2028c"]),
        ({}, b"a\nb", ["a", "b"]),
        ({}, b"\xef\xbb\xbfa\nb", ["a", "b"]),
        ({"encoding": "cp1250"}, "č\nř\n".encode("cp1250"), ["č", "ř"]),
        ({"errors": "replace"}, b"a\xff\nb", ["a\ufffd", "b"]),
    ],
)
def test_read_lines_passes_its_configuration_to_the_function(tmp_path, options, raw, expected) -> None:
    target = tmp_path / "lines.txt"
    target.write_bytes(raw)
    assert ReadLines(**options)(target) == expected


def test_read_lines_runs_asynchronously(tmp_path) -> None:
    target = tmp_path / "lines.txt"
    target.write_bytes(b"a\nb\n")
    assert asyncio.run(ReadLines().acall(target)) == ["a", "b"]
