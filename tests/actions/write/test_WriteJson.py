import asyncio
import inspect
import json
from pathlib import Path
from typing import Any
import pytest
from simplibs.actions.testing import assert_action
from simplibs.exception import AlreadyExistsError, ConversionError, StateError, ValidationError
from simplibs.file.actions import WriteJson


def _circular() -> list:
    loop: list = []
    loop.append(loop)
    return loop


def test_write_json_contract(subtests, tmp_path) -> None:
    """Verify the execution and construction contract of the WriteJson action."""
    target = tmp_path / "out" / "data.json"
    bad_options = [
        {"indent": [2]},
        {"ensure_ascii": "x"},
        {"sort_keys": "x"},
        {"allow_nan": "x"},
        {"default": 5},
        {"trailing_newline": "x"},
        {"encoding": "rot13"},
        {"newline": "\t"},
        {"overwrite": "x"},
        {"use_draft": "x"},
        {"sync": "x"},
    ]
    assert_action(
        subtests,
        WriteJson(path=target),
        valid_values=[{"a": 1}, [1, 2, 3], "text", 42, {"jméno": "Čeněk", "list": [True, False]}],
        expected_outputs=[target.resolve()] * 5,
        invalid_values=[{"x": object()}, {"s": {1, 2}}, float("nan"), _circular()],
        expected_exception_type=ConversionError,
        expected_input_type=Any,
        expected_output_type=Path,
        action_class=WriteJson,
        invalid_init_params=[((), {"path": target, **options}) for options in bad_options]
        + [((), {"path": 5}), ((), {"path": ""})],
        verbose=False,
    )


@pytest.mark.parametrize(
    ("options", "data", "expected"),
    [
        ({}, {"a": 1}, b'{\n  "a": 1\n}\n'),
        ({"indent": None}, {"a": 1}, b'{"a": 1}\n'),
        ({"indent": "\t"}, {"a": 1}, b'{\n\t"a": 1\n}\n'),
        ({"indent": None, "trailing_newline": False}, [1, 2], b"[1, 2]"),
        ({"indent": None}, {"b": 1, "a": 2}, b'{"b": 1, "a": 2}\n'),
        ({"indent": None, "sort_keys": True}, {"b": 1, "a": 2}, b'{"a": 2, "b": 1}\n'),
        ({"indent": None}, {"k": "č"}, '{"k": "č"}\n'.encode("utf-8")),
        ({"indent": None, "ensure_ascii": True}, {"k": "č"}, b'{"k": "\\u010d"}\n'),
        ({"indent": None, "allow_nan": True}, [float("nan")], b"[NaN]\n"),
        ({"indent": None, "newline": "\r\n"}, [1], b"[1]\r\n"),
    ],
)
def test_write_json_passes_its_configuration_to_the_function(tmp_path, options, data, expected) -> None:
    target = tmp_path / "deep" / "data.json"
    WriteJson(path=target, **options)(data)
    assert target.read_bytes() == expected


def test_write_json_accepts_none_as_a_value(tmp_path) -> None:
    target = tmp_path / "data.json"
    WriteJson(path=target)(None)
    assert target.read_bytes() == b"null\n"


def test_write_json_uses_the_default_function_for_custom_objects(tmp_path) -> None:
    target = tmp_path / "data.json"
    WriteJson(path=target, default=str)({"p": Path("x")})
    assert json.loads(target.read_text(encoding="utf-8")) == {"p": str(Path("x"))}


def test_write_json_custom_object_without_default_leaves_the_existing_file_intact(tmp_path) -> None:
    target = tmp_path / "data.json"
    target.write_bytes(b"old")
    with pytest.raises(ConversionError):
        WriteJson(path=target)({"x": object()})
    assert target.read_bytes() == b"old"


def test_write_json_has_no_errors_parameter(tmp_path) -> None:
    assert "errors" not in inspect.signature(WriteJson.__init__).parameters
    with pytest.raises(TypeError):
        WriteJson(path=tmp_path / "data.json", errors="strict")


@pytest.mark.parametrize("use_draft", [True, False])
def test_write_json_overwrite_false_refuses_an_existing_file(tmp_path, use_draft) -> None:
    target = tmp_path / "data.json"
    target.write_bytes(b"old")
    with pytest.raises(AlreadyExistsError):
        WriteJson(path=target, overwrite=False, use_draft=use_draft)({"a": 1})
    assert target.read_bytes() == b"old"


def test_write_json_refuses_a_directory_as_the_target(tmp_path) -> None:
    with pytest.raises(StateError):
        WriteJson(path=tmp_path)({"a": 1})


def test_write_json_runs_asynchronously(tmp_path) -> None:
    target = tmp_path / "async.json"
    result = asyncio.run(WriteJson(path=target, indent=None).acall({"a": 1}))
    assert result == target.resolve()
    assert target.read_bytes() == b'{"a": 1}\n'


def test_write_json_requires_a_path() -> None:
    with pytest.raises(TypeError):
        WriteJson()
