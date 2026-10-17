import json
import math
from pathlib import Path
import pytest
from simplibs.exception import ConversionError, NotFoundError, StateError
from simplibs.file.logic.read import read_json
from simplibs.file.logic.write import write_json


def _write(path: Path, data: bytes) -> Path:
    path.write_bytes(data)
    return path


@pytest.mark.parametrize(
    "text, expected",
    [
        ('{"a": 1, "b": [true, null, 2.5]}', {"a": 1, "b": [True, None, 2.5]}),
        ("[1, 2, 3]", [1, 2, 3]),
        ('"text"', "text"),
        ("42", 42),
        ("1.5", 1.5),
        ("true", True),
        ("null", None),
        ('  \n {"a": 1} \n\n', {"a": 1}),
    ],
    ids=["object", "list", "string", "int", "float", "bool", "null", "whitespace"],
)
def test_read_json_parses_every_kind_of_value(tmp_path: Path, text, expected) -> None:
    """Any JSON value is a valid document."""
    file = _write(tmp_path / "a.json", text.encode("utf-8"))

    assert read_json(file) == expected


def test_read_json_reads_non_ascii_text(tmp_path: Path) -> None:
    """UTF-8 text stays readable."""
    file = _write(tmp_path / "a.json", '{"město": "Plzeň"}'.encode("utf-8"))

    assert read_json(file) == {"město": "Plzeň"}


def test_read_json_tolerates_a_bom(tmp_path: Path) -> None:
    """A BOM from a Windows tool would break `json.load` on a plain utf-8 handle."""
    file = _write(tmp_path / "a.json", b"\xef\xbb\xbf" + b'{"a": 1}')

    assert read_json(file) == {"a": 1}


def test_read_json_uses_the_given_encoding(tmp_path: Path) -> None:
    """A non-UTF-8 JSON file needs its encoding."""
    file = _write(tmp_path / "a.json", '{"město": "Plzeň"}'.encode("cp1250"))

    assert read_json(file, encoding="cp1250") == {"město": "Plzeň"}


def test_read_json_accepts_nan_like_the_standard_library(tmp_path: Path) -> None:
    """`json.loads` accepts NaN; the reader does not tighten that."""
    file = _write(tmp_path / "a.json", b"[NaN]")

    assert math.isnan(read_json(file)[0])


def test_read_json_accepts_string_path(tmp_path: Path) -> None:
    """A str path works like a Path."""
    file = _write(tmp_path / "a.json", b"[1]")

    assert read_json(str(file)) == [1]


def test_read_json_round_trip_with_write_json(tmp_path: Path) -> None:
    """What write_json writes, read_json reads back."""
    file = tmp_path / "a.json"
    data = {"name": "Žlutý kůň", "numbers": [1, 2.5, None, True], "nested": {"k": "v"}}

    write_json(file, data)

    assert read_json(file) == data


# ----------------------------------------------------------------------
# Failures
# ----------------------------------------------------------------------

def test_read_json_empty_file_is_a_json_card(tmp_path: Path) -> None:
    """An empty file is not valid JSON."""
    file = _write(tmp_path / "a.json", b"")

    with pytest.raises(ConversionError) as info:
        read_json(file)

    assert info.value.error_name == "FILE_JSON_DECODE_FAILED"
    assert isinstance(info.value, json.JSONDecodeError)


@pytest.mark.parametrize(
    "text",
    ['{"a": 1,}', "{'a': 1}", '{"a": 1} // comment', "[1, 2", '{"a" 1}', "not json"],
    ids=["trailing-comma", "single-quotes", "comment", "unclosed", "missing-colon", "garbage"],
)
def test_read_json_syntax_errors_are_a_card_with_a_position(tmp_path: Path, text) -> None:
    """The syntax error carries line and column."""
    file = _write(tmp_path / "a.json", text.encode("utf-8"))

    with pytest.raises(ConversionError) as info:
        read_json(file)

    assert info.value.error_name == "FILE_JSON_DECODE_FAILED"
    assert "line 1" in str(info.value)
    assert "column" in str(info.value)


def test_read_json_position_points_to_the_right_line(tmp_path: Path) -> None:
    """The reported line is the real one."""
    file = _write(tmp_path / "a.json", b'{\n  "a": 1,\n  "b": oops\n}')

    with pytest.raises(ConversionError) as info:
        read_json(file)

    assert "line 3" in str(info.value)


def test_read_json_invalid_utf8_is_a_decode_card(tmp_path: Path) -> None:
    """Undecodable bytes are reported before any parsing."""
    file = _write(tmp_path / "a.json", b'{"a": "\xff"}')

    with pytest.raises(ConversionError) as info:
        read_json(file)

    assert info.value.error_name == "FILE_DECODE_FAILED"


def test_read_json_directory_is_a_state_error(tmp_path: Path) -> None:
    """The old version raised a raw IsADirectoryError."""
    with pytest.raises(StateError) as info:
        read_json(tmp_path)

    assert info.value.error_name == "FILE_READ_NOT_A_FILE"


def test_read_json_missing_file_raises_not_found(tmp_path: Path) -> None:
    """A missing file is NotFoundError."""
    with pytest.raises(NotFoundError) as info:
        read_json(tmp_path / "missing.json")

    assert info.value.error_name == "FILE_READ_NOT_FOUND"
