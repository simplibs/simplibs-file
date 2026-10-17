import asyncio
import inspect
import json
from pathlib import Path
import pytest
from simplibs.actions.testing import assert_action
from simplibs.exception import AlreadyExistsError, ConversionError, StateError, ValidationError
from simplibs.file.actions import WriteJsonTo
from simplibs.path.annotations import PathLike


def test_write_json_to_contract(subtests, tmp_path) -> None:
    """Verify the execution and construction contract of the WriteJsonTo action."""
    first = tmp_path / "a.json"
    second = tmp_path / "sub" / "b.json"
    ok = {"data": {"a": 1}}
    bad_options = [
        {**ok, "indent": [2]},
        {**ok, "ensure_ascii": "x"},
        {**ok, "sort_keys": "x"},
        {**ok, "allow_nan": "x"},
        {**ok, "default": 5},
        {**ok, "trailing_newline": "x"},
        {**ok, "encoding": "rot13"},
        {**ok, "newline": "\t"},
        {**ok, "overwrite": "x"},
        {**ok, "use_draft": "x"},
        {**ok, "sync": "x"},
    ]
    assert_action(
        subtests,
        WriteJsonTo(data={"a": 1}),
        valid_values=[first, str(second)],
        expected_outputs=[first.resolve(), second.resolve()],
        invalid_values=[5, "", None, tmp_path],
        expected_exception_type=[ValidationError, ValidationError, ValidationError, StateError],
        expected_input_type=PathLike,
        expected_output_type=Path,
        action_class=WriteJsonTo,
        invalid_init_params=[((), options) for options in bad_options],
        verbose=False,
    )


def test_write_json_to_writes_the_same_document_to_every_path(tmp_path) -> None:
    action = WriteJsonTo(data={"b": 1, "a": 2}, indent=None, sort_keys=True)
    targets = [tmp_path / "a.json", tmp_path / "deep" / "b.json"]
    for target in targets:
        action(target)
    assert [t.read_bytes() for t in targets] == [b'{"a": 2, "b": 1}\n'] * 2


@pytest.mark.parametrize(
    ("options", "data", "expected"),
    [
        ({}, {"a": 1}, b'{\n  "a": 1\n}\n'),
        ({"indent": None}, {"a": 1}, b'{"a": 1}\n'),
        ({"indent": None, "trailing_newline": False}, [1, 2], b"[1, 2]"),
        ({"indent": None}, {"k": "č"}, '{"k": "č"}\n'.encode("utf-8")),
        ({"indent": None, "ensure_ascii": True}, {"k": "č"}, b'{"k": "\\u010d"}\n'),
        ({"indent": None, "allow_nan": True}, [float("nan")], b"[NaN]\n"),
        ({"indent": None, "newline": "\r\n"}, [1], b"[1]\r\n"),
    ],
)
def test_write_json_to_passes_its_configuration_to_the_function(tmp_path, options, data, expected) -> None:
    target = tmp_path / "data.json"
    WriteJsonTo(data=data, **options)(target)
    assert target.read_bytes() == expected


def test_write_json_to_accepts_none_as_the_configured_data(tmp_path) -> None:
    target = tmp_path / "data.json"
    WriteJsonTo(data=None)(target)
    assert target.read_bytes() == b"null\n"


def test_write_json_to_uses_the_default_function_for_custom_objects(tmp_path) -> None:
    target = tmp_path / "data.json"
    WriteJsonTo(data={"p": Path("x")}, default=str)(target)
    assert json.loads(target.read_text(encoding="utf-8")) == {"p": str(Path("x"))}


def test_write_json_to_unserializable_data_fails_when_it_runs_and_writes_nothing(tmp_path) -> None:
    target = tmp_path / "data.json"
    with pytest.raises(ConversionError):
        WriteJsonTo(data={"x": object()})(target)
    assert not target.exists()


def test_write_json_to_has_no_errors_parameter() -> None:
    assert "errors" not in inspect.signature(WriteJsonTo.__init__).parameters
    with pytest.raises(TypeError):
        WriteJsonTo(data={}, errors="strict")


@pytest.mark.parametrize("use_draft", [True, False])
def test_write_json_to_overwrite_false_refuses_an_existing_file(tmp_path, use_draft) -> None:
    target = tmp_path / "data.json"
    target.write_bytes(b"old")
    with pytest.raises(AlreadyExistsError):
        WriteJsonTo(data={"a": 1}, overwrite=False, use_draft=use_draft)(target)
    assert target.read_bytes() == b"old"


def test_write_json_to_runs_asynchronously(tmp_path) -> None:
    target = tmp_path / "async.json"
    result = asyncio.run(WriteJsonTo(data={"a": 1}, indent=None).acall(target))
    assert result == target.resolve()
    assert target.read_bytes() == b'{"a": 1}\n'


def test_write_json_to_requires_the_data() -> None:
    with pytest.raises(TypeError):
        WriteJsonTo()
