import asyncio
from pathlib import Path
import pytest
from simplibs.actions.testing import assert_action
from simplibs.exception import AlreadyExistsError, StateError, ValidationError
from simplibs.file.actions import WriteBytes


def test_write_bytes_contract(subtests, tmp_path) -> None:
    """Verify the execution and construction contract of the WriteBytes action."""
    target = tmp_path / "out" / "blob.bin"
    bad_options = [
        {"overwrite": "x"},
        {"use_draft": "x"},
        {"sync": "x"},
    ]
    assert_action(
        subtests,
        WriteBytes(path=target),
        valid_values=[b"abc", b"", b"\x00\xff\x10", bytearray(b"ba"), memoryview(b"mv")],
        expected_outputs=[target.resolve()] * 5,
        invalid_values=[5, None],
        expected_exception_type=ValidationError,
        expected_input_type=bytes | bytearray | memoryview,
        expected_output_type=Path,
        action_class=WriteBytes,
        invalid_init_params=[((), {"path": target, **options}) for options in bad_options]
        + [((), {"path": 5}), ((), {"path": ""})],
        verbose=False,
    )


@pytest.mark.parametrize("use_draft", [True, False])
def test_write_bytes_really_writes_the_exact_bytes_and_the_folder(tmp_path, use_draft) -> None:
    target = tmp_path / "deep" / "er" / "blob.bin"
    WriteBytes(path=target, use_draft=use_draft)(b"\x00\xff\r\n")
    assert target.read_bytes() == b"\x00\xff\r\n"


@pytest.mark.parametrize("use_draft", [True, False])
def test_write_bytes_overwrite_false_refuses_an_existing_file(tmp_path, use_draft) -> None:
    target = tmp_path / "blob.bin"
    target.write_bytes(b"old")
    with pytest.raises(AlreadyExistsError):
        WriteBytes(path=target, overwrite=False, use_draft=use_draft)(b"new")
    assert target.read_bytes() == b"old"


def test_write_bytes_overwrites_by_default(tmp_path) -> None:
    target = tmp_path / "blob.bin"
    target.write_bytes(b"old")
    WriteBytes(path=target)(b"new")
    assert target.read_bytes() == b"new"


def test_write_bytes_refuses_a_directory_as_the_target(tmp_path) -> None:
    with pytest.raises(StateError):
        WriteBytes(path=tmp_path)(b"x")


def test_write_bytes_runs_asynchronously(tmp_path) -> None:
    target = tmp_path / "async.bin"
    result = asyncio.run(WriteBytes(path=target).acall(b"async"))
    assert result == target.resolve()
    assert target.read_bytes() == b"async"


def test_write_bytes_requires_a_path() -> None:
    with pytest.raises(TypeError):
        WriteBytes()
