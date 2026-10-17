import asyncio
import inspect
from pathlib import Path
import pytest
from simplibs.actions.testing import assert_action
from simplibs.exception import StateError, ValidationError
from simplibs.file.actions import AppendBytes


def test_append_bytes_contract(subtests, tmp_path) -> None:
    """Verify the execution and construction contract of the AppendBytes action."""
    target = tmp_path / "out" / "blob.bin"
    bad_options = [
        {"use_draft": "x"},
        {"sync": "x"},
    ]
    assert_action(
        subtests,
        AppendBytes(path=target),
        valid_values=[b"abc", b"", b"\x00\xff\x10", bytearray(b"ba"), memoryview(b"mv")],
        expected_outputs=[target.resolve()] * 5,
        invalid_values=[5, None],
        expected_exception_type=ValidationError,
        expected_input_type=bytes | bytearray | memoryview,
        expected_output_type=Path,
        action_class=AppendBytes,
        invalid_init_params=[((), {"path": target, **options}) for options in bad_options]
        + [((), {"path": 5}), ((), {"path": ""})],
        verbose=False,
    )


def test_append_bytes_creates_a_missing_file_and_its_folder(tmp_path) -> None:
    target = tmp_path / "deep" / "er" / "blob.bin"
    AppendBytes(path=target)(b"\x01\x02")
    assert target.read_bytes() == b"\x01\x02"


@pytest.mark.parametrize("use_draft", [False, True])
def test_append_bytes_adds_after_the_existing_content(tmp_path, use_draft) -> None:
    target = tmp_path / "blob.bin"
    target.write_bytes(b"a")
    action = AppendBytes(path=target, use_draft=use_draft)
    action(b"b")
    action(b"\x00")
    assert target.read_bytes() == b"ab\x00"


def test_append_bytes_cannot_be_told_to_overwrite(tmp_path) -> None:
    assert "overwrite" not in inspect.signature(AppendBytes.__init__).parameters
    with pytest.raises(TypeError):
        AppendBytes(path=tmp_path / "blob.bin", overwrite=True)


def test_append_bytes_refuses_a_directory_as_the_target(tmp_path) -> None:
    with pytest.raises(StateError):
        AppendBytes(path=tmp_path)(b"x")


def test_append_bytes_runs_asynchronously(tmp_path) -> None:
    target = tmp_path / "async.bin"
    result = asyncio.run(AppendBytes(path=target).acall(b"async"))
    assert result == target.resolve()
    assert target.read_bytes() == b"async"


def test_append_bytes_requires_a_path() -> None:
    with pytest.raises(TypeError):
        AppendBytes()
