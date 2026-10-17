import json
import math
import os
from pathlib import Path
import pytest
from simplibs.exception import AlreadyExistsError, ConversionError
from simplibs.file.logic.read import read_json
from simplibs.file.logic.write import write_json


def _drafts(folder: Path) -> list[Path]:
    return sorted(folder.glob(".*.draft"))


# ----------------------------------------------------------------------
# Output shape
# ----------------------------------------------------------------------

def test_write_json_default_output_is_indented_utf8_with_a_final_newline(tmp_path: Path) -> None:
    """indent=2, readable non-ASCII, trailing newline."""
    target = tmp_path / "a.json"

    write_json(target, {"město": "Plzeň", "n": [1, 2]})

    assert target.read_text(encoding="utf-8") == (
        '{\n  "město": "Plzeň",\n  "n": [\n    1,\n    2\n  ]\n}\n'
    )


def test_write_json_non_ascii_text_is_written_as_it_is(tmp_path: Path) -> None:
    """`č`, not `\\u010d`."""
    target = tmp_path / "a.json"

    write_json(target, {"k": "č"})

    assert "č".encode("utf-8") in target.read_bytes()
    assert b"\\u010d" not in target.read_bytes()


def test_write_json_ensure_ascii_escapes_non_ascii(tmp_path: Path) -> None:
    """Opt-in escaping."""
    target = tmp_path / "a.json"

    write_json(target, {"k": "č"}, ensure_ascii=True, indent=None)

    assert target.read_text(encoding="utf-8") == '{"k": "\\u010d"}\n'


def test_write_json_indent_none_is_compact(tmp_path: Path) -> None:
    """No indentation, a single line plus the final newline."""
    target = tmp_path / "a.json"

    write_json(target, {"a": 1, "b": [1, 2]}, indent=None)

    assert target.read_text(encoding="utf-8") == '{"a": 1, "b": [1, 2]}\n'


def test_write_json_indent_accepts_a_string(tmp_path: Path) -> None:
    """A tab as indentation."""
    target = tmp_path / "a.json"

    write_json(target, {"a": 1}, indent="\t")

    assert target.read_text(encoding="utf-8") == '{\n\t"a": 1\n}\n'


def test_write_json_sort_keys_gives_reproducible_output(tmp_path: Path) -> None:
    """Keys are sorted on request."""
    target = tmp_path / "a.json"

    write_json(target, {"b": 1, "a": 2}, sort_keys=True, indent=None)

    assert target.read_text(encoding="utf-8") == '{"a": 2, "b": 1}\n'


def test_write_json_keeps_insertion_order_by_default(tmp_path: Path) -> None:
    """No sorting unless asked."""
    target = tmp_path / "a.json"

    write_json(target, {"b": 1, "a": 2}, indent=None)

    assert target.read_text(encoding="utf-8") == '{"b": 1, "a": 2}\n'


def test_write_json_trailing_newline_false(tmp_path: Path) -> None:
    """The file may end right after the document."""
    target = tmp_path / "a.json"

    write_json(target, [1], indent=None, trailing_newline=False)

    assert target.read_bytes() == b"[1]"


@pytest.mark.parametrize(
    "newline, expected",
    [("\r\n", b'{\r\n  "a": 1\r\n}\r\n'), ("\n", b'{\n  "a": 1\n}\n'), (None, ('{' + os.linesep + '  "a": 1' + os.linesep + '}' + os.linesep).encode("ascii"))],
    ids=["CRLF", "LF", "platform"],
)
def test_write_json_newline_decides_the_line_ending(tmp_path: Path, newline, expected) -> None:
    """Every line ending of the document follows `newline`."""
    target = tmp_path / "a.json"

    write_json(target, {"a": 1}, newline=newline)

    assert target.read_bytes() == expected


@pytest.mark.parametrize("data", [1, 1.5, "text", True, None, [], {}, [1, "a", None], {"a": {"b": [1]}}])
def test_write_json_writes_every_kind_of_value(tmp_path: Path, data) -> None:
    """Any JSON value is a valid document."""
    target = tmp_path / "a.json"

    write_json(target, data)

    assert json.loads(target.read_text(encoding="utf-8")) == data


def test_write_json_round_trip_with_read_json(tmp_path: Path) -> None:
    """What write_json writes, read_json reads back."""
    target = tmp_path / "a.json"
    data = {"name": "Žlutý kůň", "numbers": [1, 2.5, None, True], "nested": {"k": "v"}}

    write_json(target, data)

    assert read_json(target) == data


def test_write_json_returns_the_normalized_path(tmp_path: Path) -> None:
    """The result is the absolute, resolved target."""
    assert write_json(tmp_path / "a.json", {}) == (tmp_path / "a.json").resolve()


def test_write_json_creates_missing_folders(tmp_path: Path) -> None:
    """The target's folder is guaranteed."""
    target = tmp_path / "a" / "b" / "a.json"

    write_json(target, {"a": 1})

    assert json.loads(target.read_text(encoding="utf-8")) == {"a": 1}


# ----------------------------------------------------------------------
# Custom types and special floats
# ----------------------------------------------------------------------

def test_write_json_default_converts_custom_objects(tmp_path: Path) -> None:
    """`default` turns objects JSON cannot hold into something it can."""
    target = tmp_path / "a.json"

    write_json(target, {"path": Path("a/b")}, default=str, indent=None)

    assert json.loads(target.read_text(encoding="utf-8")) == {"path": str(Path("a/b"))}


def test_write_json_nan_is_refused_by_default(tmp_path: Path) -> None:
    """NaN is not valid JSON; most parsers reject it."""
    target = tmp_path / "a.json"

    with pytest.raises(ConversionError) as info:
        write_json(target, [math.nan])

    assert info.value.error_name == "FILE_JSON_ENCODE_FAILED"
    assert isinstance(info.value, ValueError)
    assert not target.exists()


@pytest.mark.parametrize("value", [math.inf, -math.inf])
def test_write_json_infinity_is_refused_by_default(tmp_path: Path, value) -> None:
    """Infinity is not valid JSON either."""
    with pytest.raises(ConversionError):
        write_json(tmp_path / "a.json", [value])


def test_write_json_allow_nan_writes_the_token(tmp_path: Path) -> None:
    """Opt-in, as in the standard library."""
    target = tmp_path / "a.json"

    write_json(target, [math.nan], allow_nan=True, indent=None)

    assert target.read_text(encoding="utf-8") == "[NaN]\n"


# ----------------------------------------------------------------------
# Failures leave the disk alone
# ----------------------------------------------------------------------

class _Custom:
    pass


def _circular():
    data: list = []
    data.append(data)
    return data


@pytest.mark.parametrize(
    "data, expected_type, kwargs",
    [
        (_Custom(), TypeError, {}),
        (_circular(), ValueError, {}),
        ({1: "a", "b": "c"}, TypeError, {"sort_keys": True}),
        ({"a": {1, 2}}, TypeError, {}),
    ],
    ids=["custom-object", "circular", "mixed-keys-sorted", "set"],
)
@pytest.mark.parametrize("use_draft", [True, False])
def test_write_json_serialization_failure_keeps_the_existing_file(
    tmp_path: Path, data, expected_type, kwargs, use_draft,
) -> None:
    """The document is serialized in memory first, so a failure never leaves a half-written file."""
    target = tmp_path / "a.json"
    target.write_text('{"old": true}', encoding="utf-8")

    with pytest.raises(ConversionError) as info:
        write_json(target, data, use_draft=use_draft, **kwargs)

    assert info.value.error_name == "FILE_JSON_ENCODE_FAILED"
    assert isinstance(info.value, expected_type)
    assert target.read_text(encoding="utf-8") == '{"old": true}'
    assert _drafts(tmp_path) == []


# Deeper than the recursion limit of every supported Python (3.12+ counts C recursion separately)
_DEPTH = 100_000


def _too_deep() -> list:
    """A list nested far deeper than the interpreter's recursion limit."""
    data: list = []
    for _ in range(_DEPTH):
        data = [data]
    return data


@pytest.mark.parametrize("use_draft", [True, False])
def test_write_json_extremely_deep_nesting_is_a_card_not_a_bare_recursion_error(tmp_path: Path, use_draft) -> None:
    """The recursion limit is reached inside `json.dumps`; the caller still gets a ConversionError."""
    target = tmp_path / "a.json"
    target.write_text('{"old": true}', encoding="utf-8")

    with pytest.raises(ConversionError) as info:
        write_json(target, _too_deep(), use_draft=use_draft)

    assert info.value.error_name == "FILE_JSON_ENCODE_FAILED"
    assert isinstance(info.value, RecursionError)
    assert target.read_text(encoding="utf-8") == '{"old": true}'
    assert _drafts(tmp_path) == []


def test_write_json_serialization_failure_does_not_create_the_file(tmp_path: Path) -> None:
    """No file appears at all."""
    target = tmp_path / "a.json"

    with pytest.raises(ConversionError):
        write_json(target, _Custom())

    assert not target.exists()


def test_write_json_unencodable_character_is_an_encode_card(tmp_path: Path) -> None:
    """For another encoding an unencodable character is a real error."""
    target = tmp_path / "a.json"
    target.write_text("{}", encoding="utf-8")

    with pytest.raises(ConversionError) as info:
        write_json(target, {"k": "я"}, encoding="cp1250")

    assert info.value.error_name == "FILE_ENCODE_FAILED"
    assert target.read_text(encoding="utf-8") == "{}"


@pytest.mark.parametrize("use_draft", [True, False])
def test_write_json_overwrite_false_refuses_an_existing_file(tmp_path: Path, use_draft) -> None:
    """The original is untouched."""
    target = tmp_path / "a.json"
    target.write_text("{}", encoding="utf-8")

    with pytest.raises(AlreadyExistsError):
        write_json(target, {"a": 1}, overwrite=False, use_draft=use_draft)

    assert target.read_text(encoding="utf-8") == "{}"
