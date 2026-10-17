import asyncio
from pathlib import Path
import pytest
from simplibs.actions.testing import assert_action
from simplibs.exception import AlreadyExistsError, StateError, ValidationError
from simplibs.file.actions import WriteBytesTo
from simplibs.path.annotations import PathLike


def test_write_bytes_to_contract(subtests, tmp_path) -> None:
    """Verify the execution and construction contract of the WriteBytesTo action."""
    first = tmp_path / "a.bin"
    second = tmp_path / "sub" / "b.bin"
    bad_options = [
        {"data": 5},
        {"data": None},
        {"data": b"x", "overwrite": "x"},
        {"data": b"x", "use_draft": "x"},
        {"data": b"x", "sync": "x"},
    ]
    assert_action(
        subtests,
        WriteBytesTo(data=b"\x00\xff"),
        valid_values=[first, str(second)],
        expected_outputs=[first.resolve(), second.resolve()],
        invalid_values=[5, "", None, tmp_path],
        expected_exception_type=[ValidationError, ValidationError, ValidationError, StateError],
        expected_input_type=PathLike,
        expected_output_type=Path,
        action_class=WriteBytesTo,
        invalid_init_params=[((), options) for options in bad_options],
        verbose=False,
    )


@pytest.mark.parametrize("use_draft", [True, False])
def test_write_bytes_to_writes_the_configured_bytes_to_every_path(tmp_path, use_draft) -> None:
    action = WriteBytesTo(data=b"\x00\xff\r\n", use_draft=use_draft)
    targets = [tmp_path / "a.bin", tmp_path / "deep" / "er" / "b.bin"]
    for target in targets:
        action(target)
    assert [t.read_bytes() for t in targets] == [b"\x00\xff\r\n"] * 2


@pytest.mark.parametrize("use_draft", [True, False])
def test_write_bytes_to_overwrite_false_refuses_an_existing_file(tmp_path, use_draft) -> None:
    target = tmp_path / "blob.bin"
    target.write_bytes(b"old")
    with pytest.raises(AlreadyExistsError):
        WriteBytesTo(data=b"new", overwrite=False, use_draft=use_draft)(target)
    assert target.read_bytes() == b"old"


def test_write_bytes_to_overwrites_by_default(tmp_path) -> None:
    target = tmp_path / "blob.bin"
    target.write_bytes(b"old")
    WriteBytesTo(data=b"new")(target)
    assert target.read_bytes() == b"new"


def test_write_bytes_to_runs_asynchronously(tmp_path) -> None:
    target = tmp_path / "async.bin"
    result = asyncio.run(WriteBytesTo(data=b"async").acall(target))
    assert result == target.resolve()
    assert target.read_bytes() == b"async"


def test_write_bytes_to_requires_the_data() -> None:
    with pytest.raises(TypeError):
        WriteBytesTo()
