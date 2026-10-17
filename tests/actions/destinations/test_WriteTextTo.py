import asyncio
from pathlib import Path
import pytest
from simplibs.actions.testing import assert_action
from simplibs.exception import AlreadyExistsError, ConversionError, StateError, ValidationError
from simplibs.file.actions import WriteTextTo
from simplibs.path.annotations import PathLike


def test_write_text_to_contract(subtests, tmp_path) -> None:
    """Verify the execution and construction contract of the WriteTextTo action."""
    first = tmp_path / "a.txt"
    second = tmp_path / "sub" / "b.txt"
    bad_options = [
        {"text": 5},
        {"text": None},
        {"text": "x", "encoding": "rot13"},
        {"text": "x", "errors": "xmlcharrefreplace"},
        {"text": "x", "newline": "\t"},
        {"text": "x", "overwrite": "x"},
        {"text": "x", "use_draft": "x"},
        {"text": "x", "sync": "x"},
    ]
    assert_action(
        subtests,
        WriteTextTo(text="hello"),
        valid_values=[first, str(second)],
        expected_outputs=[first.resolve(), second.resolve()],
        invalid_values=[5, "", None, tmp_path],
        expected_exception_type=[ValidationError, ValidationError, ValidationError, StateError],
        expected_input_type=PathLike,
        expected_output_type=Path,
        action_class=WriteTextTo,
        invalid_init_params=[((), options) for options in bad_options],
        verbose=False,
    )


def test_write_text_to_writes_the_configured_text_to_every_path(tmp_path) -> None:
    action = WriteTextTo(text="# TODO\n")
    targets = [tmp_path / "a.txt", tmp_path / "deep" / "er" / "b.txt"]
    for target in targets:
        action(target)
    assert [t.read_bytes() for t in targets] == [b"# TODO\n"] * 2


@pytest.mark.parametrize(
    ("options", "text", "expected"),
    [
        ({"newline": "\r\n"}, "a\nb", b"a\r\nb"),
        ({"encoding": "cp1250"}, "č", "č".encode("cp1250")),
        ({"encoding": "ascii", "errors": "replace"}, "č", b"?"),
        ({"encoding": "utf-8-sig"}, "a", b"\xef\xbb\xbfa"),
    ],
)
def test_write_text_to_passes_its_configuration_to_the_function(tmp_path, options, text, expected) -> None:
    target = tmp_path / "n.txt"
    WriteTextTo(text=text, **options)(target)
    assert target.read_bytes() == expected


def test_write_text_to_unencodable_character_leaves_the_existing_file_intact(tmp_path) -> None:
    target = tmp_path / "n.txt"
    target.write_bytes(b"old")
    with pytest.raises(ConversionError):
        WriteTextTo(text="č", encoding="ascii")(target)
    assert target.read_bytes() == b"old"


@pytest.mark.parametrize("use_draft", [True, False])
def test_write_text_to_overwrite_false_refuses_an_existing_file(tmp_path, use_draft) -> None:
    target = tmp_path / "n.txt"
    target.write_bytes(b"old")
    with pytest.raises(AlreadyExistsError):
        WriteTextTo(text="new", overwrite=False, use_draft=use_draft)(target)
    assert target.read_bytes() == b"old"


def test_write_text_to_runs_asynchronously(tmp_path) -> None:
    target = tmp_path / "async.txt"
    result = asyncio.run(WriteTextTo(text="async").acall(target))
    assert result == target.resolve()
    assert target.read_bytes() == b"async"


def test_write_text_to_requires_the_text() -> None:
    with pytest.raises(TypeError):
        WriteTextTo()
