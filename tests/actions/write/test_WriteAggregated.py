import asyncio
from pathlib import Path
import pytest
from simplibs.actions.testing import assert_action
from simplibs.exception import AlreadyExistsError, ConversionError, StateError, ValidationError
from simplibs.file.actions import WriteAggregated
from simplibs.file.annotations import TextCollection


def test_write_aggregated_contract(subtests, tmp_path) -> None:
    """Verify the execution and construction contract of the WriteAggregated action."""
    target = tmp_path / "out" / "combined.txt"
    bad_options = [
        {"separator": 5},
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
        WriteAggregated(path=target),
        valid_values=[["a", "b"], [], ["Příliš žluťoučký", "kůň"]],
        expected_outputs=[target.resolve()] * 3,
        invalid_values=[5, None, [1, 2], "abc"],
        expected_exception_type=ValidationError,
        expected_input_type=TextCollection,
        expected_output_type=Path,
        action_class=WriteAggregated,
        invalid_init_params=[((), {"path": target, **options}) for options in bad_options]
        + [((), {"path": 5}), ((), {"path": ""})],
        verbose=False,
    )


@pytest.mark.parametrize(
    ("options", "parts", "expected"),
    [
        ({}, ["a", "b"], b"a\nb"),
        ({"separator": "\n\n"}, ["a", "b", "c"], b"a\n\nb\n\nc"),
        ({"separator": "---"}, ["a", "b"], b"a---b"),
        ({"separator": ""}, ["a", "b"], b"ab"),
        ({"trailing_newline": True}, ["a", "b"], b"a\nb\n"),
        ({}, [], b""),
        ({}, ["only"], b"only"),
        ({"newline": "\r\n"}, ["a", "b"], b"a\r\nb"),
        ({"encoding": "cp1250"}, ["č", "ř"], "č\nř".encode("cp1250")),
        ({"encoding": "ascii", "errors": "replace"}, ["č"], b"?"),
    ],
)
def test_write_aggregated_joins_the_parts(tmp_path, options, parts, expected) -> None:
    target = tmp_path / "deep" / "combined.txt"
    WriteAggregated(path=target, **options)(parts)
    assert target.read_bytes() == expected


def test_write_aggregated_unencodable_character_leaves_the_existing_file_intact(tmp_path) -> None:
    target = tmp_path / "combined.txt"
    target.write_bytes(b"old")
    with pytest.raises(ConversionError):
        WriteAggregated(path=target, encoding="ascii")(["č"])
    assert target.read_bytes() == b"old"


@pytest.mark.parametrize("use_draft", [True, False])
def test_write_aggregated_overwrite_false_refuses_an_existing_file(tmp_path, use_draft) -> None:
    target = tmp_path / "combined.txt"
    target.write_bytes(b"old")
    with pytest.raises(AlreadyExistsError):
        WriteAggregated(path=target, overwrite=False, use_draft=use_draft)(["new"])
    assert target.read_bytes() == b"old"


def test_write_aggregated_refuses_a_directory_as_the_target(tmp_path) -> None:
    with pytest.raises(StateError):
        WriteAggregated(path=tmp_path)(["x"])


def test_write_aggregated_runs_asynchronously(tmp_path) -> None:
    target = tmp_path / "async.txt"
    result = asyncio.run(WriteAggregated(path=target).acall(["a", "b"]))
    assert result == target.resolve()
    assert target.read_bytes() == b"a\nb"


def test_write_aggregated_requires_a_path() -> None:
    with pytest.raises(TypeError):
        WriteAggregated()
