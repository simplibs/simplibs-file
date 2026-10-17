import asyncio
from pathlib import Path
import pytest
from simplibs.actions.testing import assert_action
from simplibs.exception import ConversionError, NotFoundError, StateError, ValidationError
from simplibs.file.actions import ReadText
from simplibs.path.annotations import PathLike


def test_read_text_contract(subtests, tmp_path) -> None:
    """Verify the execution and construction contract of the ReadText action."""
    plain = tmp_path / "plain.txt"
    plain.write_bytes("Příliš žluťoučký kůň".encode("utf-8"))
    bom = tmp_path / "bom.txt"
    bom.write_bytes(b"\xef\xbb\xbfhello")
    mixed = tmp_path / "mixed.txt"
    mixed.write_bytes(b"a\r\nb\rc\nd")
    empty = tmp_path / "empty.txt"
    empty.write_bytes(b"")
    broken = tmp_path / "broken.txt"
    broken.write_bytes(b"\xff\xfe\xfa")
    assert_action(
        subtests,
        ReadText(),
        valid_values=[plain, str(bom), mixed, empty],
        expected_outputs=["Příliš žluťoučký kůň", "hello", "a\nb\nc\nd", ""],
        invalid_values=[5, "", tmp_path / "missing", tmp_path, broken],
        expected_exception_type=[
            ValidationError,
            ValidationError,
            NotFoundError,
            StateError,
            ConversionError,
        ],
        expected_input_type=PathLike,
        expected_output_type=str,
        action_class=ReadText,
        invalid_init_params=[
            ((), {"encoding": "rot13"}),
            ((), {"encoding": ""}),
            ((), {"encoding": 5}),
            ((), {"errors": "xmlcharrefreplace"}),
            ((), {"errors": "bogus"}),
            ((), {"errors": 5}),
        ],
        verbose=False,
    )


@pytest.mark.parametrize(
    ("options", "raw", "expected"),
    [
        ({"encoding": "cp1250"}, "č".encode("cp1250"), "č"),
        ({"encoding": "utf-16"}, "ab".encode("utf-16"), "ab"),
        ({"encoding": "utf-8"}, b"\xef\xbb\xbfa", "\ufeffa"),
        ({"errors": "replace"}, b"a\xffb", "a\ufffdb"),
        ({"errors": "ignore"}, b"a\xffb", "ab"),
    ],
)
def test_read_text_passes_its_configuration_to_the_function(tmp_path, options, raw, expected) -> None:
    target = tmp_path / "t.txt"
    target.write_bytes(raw)
    assert ReadText(**options)(target) == expected


def test_read_text_undecodable_bytes_fail_with_strict_errors(tmp_path) -> None:
    target = tmp_path / "t.txt"
    target.write_bytes(b"a\xffb")
    with pytest.raises(ConversionError):
        ReadText()(target)


def test_read_text_runs_asynchronously(tmp_path) -> None:
    target = tmp_path / "t.txt"
    target.write_bytes(b"a\r\nb")
    assert asyncio.run(ReadText().acall(target)) == "a\nb"
