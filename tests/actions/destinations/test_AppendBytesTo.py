import asyncio
import inspect
from pathlib import Path
import pytest
from simplibs.actions.testing import assert_action
from simplibs.exception import StateError, ValidationError
from simplibs.file.actions import AppendBytesTo
from simplibs.path.annotations import PathLike


def test_append_bytes_to_contract(subtests, tmp_path) -> None:
    """Verify the execution and construction contract of the AppendBytesTo action."""
    first = tmp_path / "a.bin"
    second = tmp_path / "sub" / "b.bin"
    bad_options = [
        {"data": 5},
        {"data": None},
        {"data": b"x", "use_draft": "x"},
        {"data": b"x", "sync": "x"},
    ]
    assert_action(
        subtests,
        AppendBytesTo(data=b"\x00\xff"),
        valid_values=[first, str(second)],
        expected_outputs=[first.resolve(), second.resolve()],
        invalid_values=[5, "", None, tmp_path],
        expected_exception_type=[ValidationError, ValidationError, ValidationError, StateError],
        expected_input_type=PathLike,
        expected_output_type=Path,
        action_class=AppendBytesTo,
        invalid_init_params=[((), options) for options in bad_options],
        verbose=False,
    )


@pytest.mark.parametrize("use_draft", [False, True])
def test_append_bytes_to_appends_to_every_path(tmp_path, use_draft) -> None:
    action = AppendBytesTo(data=b"\x00", use_draft=use_draft)
    first = tmp_path / "a.bin"
    second = tmp_path / "deep" / "b.bin"
    first.write_bytes(b"1")
    action(first)
    action(first)
    action(second)
    assert first.read_bytes() == b"1\x00\x00"
    assert second.read_bytes() == b"\x00"


def test_append_bytes_to_cannot_be_told_to_overwrite() -> None:
    assert "overwrite" not in inspect.signature(AppendBytesTo.__init__).parameters
    with pytest.raises(TypeError):
        AppendBytesTo(data=b"x", overwrite=True)


def test_append_bytes_to_runs_asynchronously(tmp_path) -> None:
    target = tmp_path / "async.bin"
    result = asyncio.run(AppendBytesTo(data=b"async").acall(target))
    assert result == target.resolve()
    assert target.read_bytes() == b"async"


def test_append_bytes_to_requires_the_data() -> None:
    with pytest.raises(TypeError):
        AppendBytesTo()
