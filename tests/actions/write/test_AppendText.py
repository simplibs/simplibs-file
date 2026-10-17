import asyncio
import inspect
from pathlib import Path
import pytest
from simplibs.actions.testing import assert_action
from simplibs.exception import ConversionError, StateError, ValidationError
from simplibs.file.actions import AppendText


def test_append_text_contract(subtests, tmp_path) -> None:
    """Verify the execution and construction contract of the AppendText action."""
    target = tmp_path / "out" / "log.txt"
    bad_options = [
        {"encoding": "rot13"},
        {"errors": "xmlcharrefreplace"},
        {"newline": "\t"},
        {"use_draft": "x"},
        {"sync": "x"},
    ]
    assert_action(
        subtests,
        AppendText(path=target),
        valid_values=["hello", "", "Příliš žluťoučký kůň\n"],
        expected_outputs=[target.resolve()] * 3,
        invalid_values=[5, None],
        expected_exception_type=ValidationError,
        expected_input_type=str,
        expected_output_type=Path,
        action_class=AppendText,
        invalid_init_params=[((), {"path": target, **options}) for options in bad_options]
        + [((), {"path": 5}), ((), {"path": ""})],
        verbose=False,
    )


def test_append_text_creates_a_missing_file_and_its_folder(tmp_path) -> None:
    target = tmp_path / "deep" / "er" / "log.txt"
    AppendText(path=target)("first")
    assert target.read_bytes() == b"first"


@pytest.mark.parametrize("use_draft", [False, True])
def test_append_text_adds_after_the_existing_content(tmp_path, use_draft) -> None:
    target = tmp_path / "log.txt"
    target.write_bytes(b"a")
    action = AppendText(path=target, use_draft=use_draft)
    action("b")
    action("c")
    assert target.read_bytes() == b"abc"


@pytest.mark.parametrize(
    ("options", "text", "expected"),
    [
        ({"newline": "\r\n"}, "a\nb", b"a\r\nb"),
        ({"encoding": "cp1250"}, "č", "č".encode("cp1250")),
        ({"encoding": "ascii", "errors": "replace"}, "č", b"?"),
    ],
)
def test_append_text_passes_its_configuration_to_the_function(tmp_path, options, text, expected) -> None:
    target = tmp_path / "log.txt"
    AppendText(path=target, **options)(text)
    assert target.read_bytes() == expected


def test_append_text_unencodable_character_leaves_the_file_untouched(tmp_path) -> None:
    target = tmp_path / "log.txt"
    target.write_bytes(b"old")
    with pytest.raises(ConversionError):
        AppendText(path=target, encoding="ascii")("č")
    assert target.read_bytes() == b"old"


def test_append_text_cannot_be_told_to_overwrite(tmp_path) -> None:
    assert "overwrite" not in inspect.signature(AppendText.__init__).parameters
    with pytest.raises(TypeError):
        AppendText(path=tmp_path / "log.txt", overwrite=True)


def test_append_text_refuses_a_directory_as_the_target(tmp_path) -> None:
    with pytest.raises(StateError):
        AppendText(path=tmp_path)("x")


def test_append_text_runs_asynchronously(tmp_path) -> None:
    target = tmp_path / "async.txt"
    result = asyncio.run(AppendText(path=target).acall("async"))
    assert result == target.resolve()
    assert target.read_bytes() == b"async"


def test_append_text_requires_a_path() -> None:
    with pytest.raises(TypeError):
        AppendText()
