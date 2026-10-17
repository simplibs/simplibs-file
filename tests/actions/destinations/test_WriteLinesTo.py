import asyncio
from pathlib import Path
import pytest
from simplibs.actions.testing import assert_action
from simplibs.exception import AlreadyExistsError, ConversionError, StateError, ValidationError
from simplibs.file.actions import WriteLinesTo
from simplibs.path.annotations import PathLike


def test_write_lines_to_contract(subtests, tmp_path) -> None:
    """Verify the execution and construction contract of the WriteLinesTo action."""
    first = tmp_path / "a.txt"
    second = tmp_path / "sub" / "b.txt"
    ok = {"lines": ["x"]}
    bad_options = [
        {"lines": 5},
        {"lines": None},
        {"lines": [1, 2]},
        {**ok, "encoding": "rot13"},
        {**ok, "errors": "xmlcharrefreplace"},
        {**ok, "newline": "\t"},
        {**ok, "trailing_newline": "x"},
        {**ok, "overwrite": "x"},
        {**ok, "use_draft": "x"},
        {**ok, "sync": "x"},
    ]
    assert_action(
        subtests,
        WriteLinesTo(lines=["a", "b"]),
        valid_values=[first, str(second)],
        expected_outputs=[first.resolve(), second.resolve()],
        invalid_values=[5, "", None, tmp_path],
        expected_exception_type=[ValidationError, ValidationError, ValidationError, StateError],
        expected_input_type=PathLike,
        expected_output_type=Path,
        action_class=WriteLinesTo,
        invalid_init_params=[((), options) for options in bad_options],
        verbose=False,
    )


def test_write_lines_to_writes_the_same_lines_to_every_path(tmp_path) -> None:
    action = WriteLinesTo(lines=["*.pyc", "__pycache__"])
    targets = [tmp_path / "a.ignore", tmp_path / "deep" / "b.ignore"]
    for target in targets:
        action(target)
    assert [t.read_bytes() for t in targets] == [b"*.pyc\n__pycache__\n"] * 2


@pytest.mark.parametrize(
    ("options", "lines", "expected"),
    [
        ({}, ["a", "b"], b"a\nb\n"),
        ({"trailing_newline": False}, ["a", "b"], b"a\nb"),
        ({}, [], b""),
        ({"newline": "\r\n"}, ["a", "b"], b"a\r\nb\r\n"),
        ({"encoding": "cp1250"}, ["č"], "č\n".encode("cp1250")),
        ({"encoding": "ascii", "errors": "replace"}, ["č"], b"?\n"),
    ],
)
def test_write_lines_to_passes_its_configuration_to_the_function(tmp_path, options, lines, expected) -> None:
    target = tmp_path / "lines.txt"
    WriteLinesTo(lines=lines, **options)(target)
    assert target.read_bytes() == expected


def test_write_lines_to_unencodable_character_leaves_the_existing_file_intact(tmp_path) -> None:
    target = tmp_path / "lines.txt"
    target.write_bytes(b"old")
    with pytest.raises(ConversionError):
        WriteLinesTo(lines=["č"], encoding="ascii")(target)
    assert target.read_bytes() == b"old"


@pytest.mark.parametrize("use_draft", [True, False])
def test_write_lines_to_overwrite_false_refuses_an_existing_file(tmp_path, use_draft) -> None:
    target = tmp_path / "lines.txt"
    target.write_bytes(b"old")
    with pytest.raises(AlreadyExistsError):
        WriteLinesTo(lines=["new"], overwrite=False, use_draft=use_draft)(target)
    assert target.read_bytes() == b"old"


def test_write_lines_to_runs_asynchronously(tmp_path) -> None:
    target = tmp_path / "async.txt"
    result = asyncio.run(WriteLinesTo(lines=["a", "b"]).acall(target))
    assert result == target.resolve()
    assert target.read_bytes() == b"a\nb\n"


def test_write_lines_to_requires_the_lines() -> None:
    with pytest.raises(TypeError):
        WriteLinesTo()
