import asyncio
from collections.abc import Collection
from pathlib import Path
import pytest
from simplibs.actions.testing import assert_action
from simplibs.exception import AlreadyExistsError, ConversionError, StateError, ValidationError
from simplibs.file.actions import WriteLines


def test_write_lines_contract(subtests, tmp_path) -> None:
    """Verify the execution and construction contract of the WriteLines action."""
    target = tmp_path / "out" / "lines.txt"
    bad_options = [
        {"encoding": "rot13"},
        {"errors": "xmlcharrefreplace"},
        {"newline": "\t"},
        {"trailing_newline": "x"},
        {"overwrite": "x"},
        {"use_draft": "x"},
        {"sync": "x"},
    ]
    assert_action(
        subtests,
        WriteLines(path=target),
        valid_values=[["a", "b"], [], ["Příliš", "žluťoučký", "kůň"]],
        expected_outputs=[target.resolve()] * 3,
        invalid_values=[5, None, [1, 2]],
        expected_exception_type=ValidationError,
        expected_input_type=Collection[str],
        expected_output_type=Path,
        action_class=WriteLines,
        invalid_init_params=[((), {"path": target, **options}) for options in bad_options]
        + [((), {"path": 5}), ((), {"path": ""})],
        verbose=False,
    )


@pytest.mark.parametrize(
    ("options", "lines", "expected"),
    [
        ({}, ["a", "b"], b"a\nb\n"),
        ({"trailing_newline": False}, ["a", "b"], b"a\nb"),
        ({}, [], b""),
        ({"trailing_newline": True}, [], b""),
        ({"newline": "\r\n"}, ["a", "b"], b"a\r\nb\r\n"),
        ({"encoding": "cp1250"}, ["č"], "č\n".encode("cp1250")),
        ({"encoding": "ascii", "errors": "replace"}, ["č"], b"?\n"),
    ],
)
def test_write_lines_writes_one_line_per_item(tmp_path, options, lines, expected) -> None:
    target = tmp_path / "deep" / "lines.txt"
    WriteLines(path=target, **options)(lines)
    assert target.read_bytes() == expected


def test_write_lines_unencodable_character_leaves_the_existing_file_intact(tmp_path) -> None:
    target = tmp_path / "lines.txt"
    target.write_bytes(b"old")
    with pytest.raises(ConversionError):
        WriteLines(path=target, encoding="ascii")(["č"])
    assert target.read_bytes() == b"old"


@pytest.mark.parametrize("use_draft", [True, False])
def test_write_lines_overwrite_false_refuses_an_existing_file(tmp_path, use_draft) -> None:
    target = tmp_path / "lines.txt"
    target.write_bytes(b"old")
    with pytest.raises(AlreadyExistsError):
        WriteLines(path=target, overwrite=False, use_draft=use_draft)(["new"])
    assert target.read_bytes() == b"old"


def test_write_lines_refuses_a_directory_as_the_target(tmp_path) -> None:
    with pytest.raises(StateError):
        WriteLines(path=tmp_path)(["x"])


def test_write_lines_runs_asynchronously(tmp_path) -> None:
    target = tmp_path / "async.txt"
    result = asyncio.run(WriteLines(path=target).acall(["a", "b"]))
    assert result == target.resolve()
    assert target.read_bytes() == b"a\nb\n"


def test_write_lines_requires_a_path() -> None:
    with pytest.raises(TypeError):
        WriteLines()
