import asyncio
from pathlib import Path
import pytest
from simplibs.actions.testing import assert_action
from simplibs.exception import AlreadyExistsError, ConversionError, StateError, ValidationError
from simplibs.file.actions import WriteText


def test_write_text_contract(subtests, tmp_path) -> None:
    """Verify the execution and construction contract of the WriteText action."""
    target = tmp_path / "out" / "note.txt"
    bad_options = [
        {"encoding": "rot13"},
        {"errors": "xmlcharrefreplace"},
        {"newline": "\t"},
        {"overwrite": "x"},
        {"use_draft": "x"},
        {"sync": "x"},
    ]
    assert_action(
        subtests,
        WriteText(path=target),
        valid_values=["hello", "", "Příliš žluťoučký kůň\núpěl ďábelské ódy"],
        expected_outputs=[target.resolve()] * 3,
        invalid_values=[5, None],
        expected_exception_type=ValidationError,
        expected_input_type=str,
        expected_output_type=Path,
        action_class=WriteText,
        invalid_init_params=[((), {"path": target, **options}) for options in bad_options]
        + [((), {"path": 5}), ((), {"path": ""})],
        verbose=False,
    )


def test_write_text_really_writes_the_file_and_its_folder(tmp_path) -> None:
    target = tmp_path / "deep" / "er" / "note.txt"
    WriteText(path=target)("ahoj")
    assert target.read_bytes() == b"ahoj"


@pytest.mark.parametrize(
    ("options", "text", "expected"),
    [
        ({"newline": "\r\n"}, "a\nb", b"a\r\nb"),
        ({"newline": "\r"}, "a\nb", b"a\rb"),
        ({"encoding": "cp1250"}, "č", "č".encode("cp1250")),
        ({"encoding": "ascii", "errors": "replace"}, "č", b"?"),
        ({"encoding": "utf-8-sig"}, "a", b"\xef\xbb\xbfa"),
    ],
)
def test_write_text_passes_its_configuration_to_the_function(tmp_path, options, text, expected) -> None:
    target = tmp_path / "n.txt"
    WriteText(path=target, **options)(text)
    assert target.read_bytes() == expected


def test_write_text_unencodable_character_leaves_the_existing_file_intact(tmp_path) -> None:
    target = tmp_path / "n.txt"
    target.write_bytes(b"old")
    with pytest.raises(ConversionError):
        WriteText(path=target, encoding="ascii")("č")
    assert target.read_bytes() == b"old"


@pytest.mark.parametrize("use_draft", [True, False])
def test_write_text_overwrite_false_refuses_an_existing_file(tmp_path, use_draft) -> None:
    target = tmp_path / "n.txt"
    target.write_bytes(b"old")
    with pytest.raises(AlreadyExistsError):
        WriteText(path=target, overwrite=False, use_draft=use_draft)("new")
    assert target.read_bytes() == b"old"


def test_write_text_overwrites_by_default(tmp_path) -> None:
    target = tmp_path / "n.txt"
    target.write_bytes(b"old")
    WriteText(path=target)("new")
    assert target.read_bytes() == b"new"


def test_write_text_refuses_a_directory_as_the_target(tmp_path) -> None:
    with pytest.raises(StateError):
        WriteText(path=tmp_path)("x")


def test_write_text_runs_asynchronously(tmp_path) -> None:
    target = tmp_path / "async.txt"
    result = asyncio.run(WriteText(path=target).acall("async"))
    assert result == target.resolve()
    assert target.read_bytes() == b"async"


def test_write_text_requires_a_path() -> None:
    with pytest.raises(TypeError):
        WriteText()
