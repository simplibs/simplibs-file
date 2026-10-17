import asyncio
import inspect
from pathlib import Path
import pytest
from simplibs.actions.testing import assert_action
from simplibs.exception import ConversionError, StateError, ValidationError
from simplibs.file.actions import AppendTextTo
from simplibs.path.annotations import PathLike


def test_append_text_to_contract(subtests, tmp_path) -> None:
    """Verify the execution and construction contract of the AppendTextTo action."""
    first = tmp_path / "a.txt"
    second = tmp_path / "sub" / "b.txt"
    bad_options = [
        {"text": 5},
        {"text": None},
        {"text": "x", "encoding": "rot13"},
        {"text": "x", "errors": "xmlcharrefreplace"},
        {"text": "x", "newline": "\t"},
        {"text": "x", "use_draft": "x"},
        {"text": "x", "sync": "x"},
    ]
    assert_action(
        subtests,
        AppendTextTo(text="line\n"),
        valid_values=[first, str(second)],
        expected_outputs=[first.resolve(), second.resolve()],
        invalid_values=[5, "", None, tmp_path],
        expected_exception_type=[ValidationError, ValidationError, ValidationError, StateError],
        expected_input_type=PathLike,
        expected_output_type=Path,
        action_class=AppendTextTo,
        invalid_init_params=[((), options) for options in bad_options],
        verbose=False,
    )


def test_append_text_to_adds_the_configured_text_to_every_path(tmp_path) -> None:
    action = AppendTextTo(text="x")
    first = tmp_path / "a.txt"
    second = tmp_path / "deep" / "b.txt"
    first.write_bytes(b"1")
    action(first)
    action(first)
    action(second)
    assert first.read_bytes() == b"1xx"
    assert second.read_bytes() == b"x"


@pytest.mark.parametrize("use_draft", [False, True])
def test_append_text_to_appends_after_existing_content(tmp_path, use_draft) -> None:
    target = tmp_path / "log.txt"
    target.write_bytes(b"a")
    AppendTextTo(text="b", use_draft=use_draft)(target)
    assert target.read_bytes() == b"ab"


@pytest.mark.parametrize(
    ("options", "text", "expected"),
    [
        ({"newline": "\r\n"}, "a\nb", b"a\r\nb"),
        ({"encoding": "cp1250"}, "č", "č".encode("cp1250")),
        ({"encoding": "ascii", "errors": "replace"}, "č", b"?"),
    ],
)
def test_append_text_to_passes_its_configuration_to_the_function(tmp_path, options, text, expected) -> None:
    target = tmp_path / "log.txt"
    AppendTextTo(text=text, **options)(target)
    assert target.read_bytes() == expected


def test_append_text_to_unencodable_character_leaves_the_file_untouched(tmp_path) -> None:
    target = tmp_path / "log.txt"
    target.write_bytes(b"old")
    with pytest.raises(ConversionError):
        AppendTextTo(text="č", encoding="ascii")(target)
    assert target.read_bytes() == b"old"


def test_append_text_to_cannot_be_told_to_overwrite() -> None:
    assert "overwrite" not in inspect.signature(AppendTextTo.__init__).parameters
    with pytest.raises(TypeError):
        AppendTextTo(text="x", overwrite=True)


def test_append_text_to_runs_asynchronously(tmp_path) -> None:
    target = tmp_path / "async.txt"
    result = asyncio.run(AppendTextTo(text="async").acall(target))
    assert result == target.resolve()
    assert target.read_bytes() == b"async"


def test_append_text_to_requires_the_text() -> None:
    with pytest.raises(TypeError):
        AppendTextTo()
