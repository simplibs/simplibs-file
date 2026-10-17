import asyncio
from pathlib import Path
import pytest
from simplibs.actions.testing import assert_action
from simplibs.exception import AlreadyExistsError, NotFoundError, ParamError, StateError, ValidationError
from simplibs.file.actions import CopyFileFrom
from simplibs.path.annotations import PathLike


def test_copy_file_from_contract(subtests, tmp_path) -> None:
    """Verify the execution and construction contract of the CopyFileFrom action."""
    template = tmp_path / "template.txt"
    template.write_text("T")
    first = tmp_path / "out" / "a.txt"
    second = tmp_path / "b.txt"
    assert_action(
        subtests,
        CopyFileFrom(source=template),
        valid_values=[first, str(second)],
        expected_outputs=[first.resolve(), second.resolve()],
        invalid_values=[5, "", tmp_path],
        expected_exception_type=[ValidationError, ValidationError, StateError],
        expected_input_type=PathLike,
        expected_output_type=Path,
        action_class=CopyFileFrom,
        invalid_init_params=[
            ((), {"source": 5}),
            ((), {"source": ""}),
            ((), {"source": None}),
            ((), {"source": template, "overwrite": "x"}),
            ((), {"source": template, "sync": "x"}),
        ],
        verbose=False,
    )


def test_copy_file_from_copies_one_template_to_every_destination(tmp_path) -> None:
    template = tmp_path / "template.bin"
    template.write_bytes(b"\x00template")
    action = CopyFileFrom(source=template)
    destinations = [tmp_path / "a.bin", tmp_path / "deep" / "er" / "b.bin"]
    for destination in destinations:
        action(destination)
    assert [d.read_bytes() for d in destinations] == [b"\x00template"] * 2
    assert template.read_bytes() == b"\x00template"


def test_copy_file_from_missing_source_fails_when_it_runs(tmp_path) -> None:
    with pytest.raises(NotFoundError):
        CopyFileFrom(source=tmp_path / "missing.txt")(tmp_path / "copy.txt")


def test_copy_file_from_overwrite_false_refuses_an_existing_destination(tmp_path) -> None:
    template = tmp_path / "template.txt"
    template.write_text("new")
    destination = tmp_path / "copy.txt"
    destination.write_text("old")
    with pytest.raises(AlreadyExistsError):
        CopyFileFrom(source=template)(destination)
    assert destination.read_text() == "old"


def test_copy_file_from_overwrite_true_replaces_the_destination(tmp_path) -> None:
    template = tmp_path / "template.txt"
    template.write_text("new")
    destination = tmp_path / "copy.txt"
    destination.write_text("old")
    CopyFileFrom(source=template, overwrite=True)(destination)
    assert destination.read_text() == "new"


def test_copy_file_from_refuses_copying_a_file_onto_itself(tmp_path) -> None:
    template = tmp_path / "template.txt"
    template.write_text("x")
    with pytest.raises(ParamError):
        CopyFileFrom(source=template, overwrite=True)(template)


def test_copy_file_from_runs_asynchronously(tmp_path) -> None:
    template = tmp_path / "template.txt"
    template.write_text("async")
    destination = tmp_path / "copy.txt"
    result = asyncio.run(CopyFileFrom(source=template).acall(destination))
    assert result == destination.resolve()
    assert destination.read_text() == "async"


def test_copy_file_from_requires_a_source() -> None:
    with pytest.raises(TypeError):
        CopyFileFrom()
