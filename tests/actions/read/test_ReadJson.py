import asyncio
import math
from pathlib import Path
from typing import Any
import pytest
from simplibs.actions.testing import assert_action
from simplibs.exception import ConversionError, NotFoundError, StateError, ValidationError
from simplibs.file.actions import ReadJson
from simplibs.path.annotations import PathLike


def test_read_json_contract(subtests, tmp_path) -> None:
    """Verify the execution and construction contract of the ReadJson action."""
    obj = tmp_path / "obj.json"
    obj.write_bytes('{"a": 1, "jméno": "Čeněk"}'.encode("utf-8"))
    array = tmp_path / "array.json"
    array.write_bytes(b"[1, 2, 3]")
    bom = tmp_path / "bom.json"
    bom.write_bytes(b'\xef\xbb\xbf{"k": "v"}')
    null = tmp_path / "null.json"
    null.write_bytes(b"null")
    empty = tmp_path / "empty.json"
    empty.write_bytes(b"")
    syntax = tmp_path / "syntax.json"
    syntax.write_bytes(b"{bad")
    broken = tmp_path / "broken.json"
    broken.write_bytes(b"\xff\xfe\xfa")
    assert_action(
        subtests,
        ReadJson(),
        valid_values=[obj, str(array), bom, null],
        expected_outputs=[{"a": 1, "jméno": "Čeněk"}, [1, 2, 3], {"k": "v"}, None],
        invalid_values=[5, "", tmp_path / "missing", tmp_path, empty, syntax, broken],
        expected_exception_type=[
            ValidationError,
            ValidationError,
            NotFoundError,
            StateError,
            ConversionError,
            ConversionError,
            ConversionError,
        ],
        expected_input_type=PathLike,
        expected_output_type=Any,
        action_class=ReadJson,
        invalid_init_params=[
            ((), {"encoding": "rot13"}),
            ((), {"encoding": ""}),
            ((), {"errors": "xmlcharrefreplace"}),
            ((), {"errors": "bogus"}),
        ],
        verbose=False,
    )


@pytest.mark.parametrize(
    ("options", "raw", "expected"),
    [
        ({"encoding": "cp1250"}, '{"k": "č"}'.encode("cp1250"), {"k": "č"}),
        ({"encoding": "utf-16"}, '{"k": 1}'.encode("utf-16"), {"k": 1}),
        ({"errors": "replace"}, b'{"k": "a\xffb"}', {"k": "a\ufffdb"}),
    ],
)
def test_read_json_passes_its_configuration_to_the_function(tmp_path, options, raw, expected) -> None:
    target = tmp_path / "data.json"
    target.write_bytes(raw)
    assert ReadJson(**options)(target) == expected


def test_read_json_accepts_nan_like_the_standard_library(tmp_path) -> None:
    target = tmp_path / "nan.json"
    target.write_bytes(b"[NaN]")
    assert math.isnan(ReadJson()(target)[0])


def test_read_json_runs_asynchronously(tmp_path) -> None:
    target = tmp_path / "data.json"
    target.write_bytes(b'{"a": 1}')
    assert asyncio.run(ReadJson().acall(target)) == {"a": 1}
