import asyncio
from pathlib import Path
import pytest
from simplibs.actions.testing import assert_action
from simplibs.exception import AlreadyExistsError, ConversionError, StateError, ValidationError
from simplibs.file.actions import WriteAggregatedTo
from simplibs.path.annotations import PathLike


def test_write_aggregated_to_contract(subtests, tmp_path) -> None:
    """Verify the execution and construction contract of the WriteAggregatedTo action."""
    first = tmp_path / "a.txt"
    second = tmp_path / "sub" / "b.txt"
    ok = {"parts": ["x"]}
    bad_options = [
        {"parts": 5},
        {"parts": None},
        {"parts": [1, 2]},
        {**ok, "separator": 5},
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
        WriteAggregatedTo(parts=["a", "b"]),
        valid_values=[first, str(second)],
        expected_outputs=[first.resolve(), second.resolve()],
        invalid_values=[5, "", None, tmp_path],
        expected_exception_type=[ValidationError, ValidationError, ValidationError, StateError],
        expected_input_type=PathLike,
        expected_output_type=Path,
        action_class=WriteAggregatedTo,
        invalid_init_params=[((), options) for options in bad_options],
        verbose=False,
    )


def test_write_aggregated_to_writes_the_same_document_to_every_path(tmp_path) -> None:
    action = WriteAggregatedTo(parts=["head", "body"], separator="\n\n")
    targets = [tmp_path / "a.txt", tmp_path / "deep" / "b.txt"]
    for target in targets:
        action(target)
    assert [t.read_bytes() for t in targets] == [b"head\n\nbody"] * 2


@pytest.mark.parametrize(
    ("options", "parts", "expected"),
    [
        ({}, ["a", "b"], b"a\nb"),
        ({"separator": ""}, ["a", "b"], b"ab"),
        ({"separator": "---"}, ["a", "b"], b"a---b"),
        ({"trailing_newline": True}, ["a", "b"], b"a\nb\n"),
        ({}, [], b""),
        ({"newline": "\r\n"}, ["a", "b"], b"a\r\nb"),
        ({"encoding": "cp1250"}, ["č", "ř"], "č\nř".encode("cp1250")),
        ({"encoding": "ascii", "errors": "replace"}, ["č"], b"?"),
    ],
)
def test_write_aggregated_to_passes_its_configuration_to_the_function(tmp_path, options, parts, expected) -> None:
    target = tmp_path / "combined.txt"
    WriteAggregatedTo(parts=parts, **options)(target)
    assert target.read_bytes() == expected


def test_write_aggregated_to_unencodable_character_leaves_the_existing_file_intact(tmp_path) -> None:
    target = tmp_path / "combined.txt"
    target.write_bytes(b"old")
    with pytest.raises(ConversionError):
        WriteAggregatedTo(parts=["č"], encoding="ascii")(target)
    assert target.read_bytes() == b"old"


@pytest.mark.parametrize("use_draft", [True, False])
def test_write_aggregated_to_overwrite_false_refuses_an_existing_file(tmp_path, use_draft) -> None:
    target = tmp_path / "combined.txt"
    target.write_bytes(b"old")
    with pytest.raises(AlreadyExistsError):
        WriteAggregatedTo(parts=["new"], overwrite=False, use_draft=use_draft)(target)
    assert target.read_bytes() == b"old"


def test_write_aggregated_to_runs_asynchronously(tmp_path) -> None:
    target = tmp_path / "async.txt"
    result = asyncio.run(WriteAggregatedTo(parts=["a", "b"]).acall(target))
    assert result == target.resolve()
    assert target.read_bytes() == b"a\nb"


def test_write_aggregated_to_requires_the_parts() -> None:
    with pytest.raises(TypeError):
        WriteAggregatedTo()
