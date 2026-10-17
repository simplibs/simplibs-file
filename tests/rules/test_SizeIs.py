from pathlib import Path
import pytest
from simplibs.exception import ParamError, ValidationError
from simplibs.exception.testing import assert_exception_function, Kwargs
from simplibs.file.rules import SizeIs
from simplibs.path.logic.scanners import collect_paths
from simplibs.path.rules import IsFile
from simplibs.rules.predicates.comparisons import GreaterThan, InRange, LessThan
from simplibs.rules.testing import assert_rule_contract


def test_size_is_contract(subtests, tmp_path) -> None:
    """Verify the complete contract of the SizeIs rule."""
    full = tmp_path / "full.bin"
    full.write_bytes(b"12345")
    empty = tmp_path / "empty.bin"
    empty.write_bytes(b"")
    folder = tmp_path / "folder"
    folder.mkdir()
    missing = tmp_path / "missing"
    assert_rule_contract(
        subtests,
        rule=SizeIs(GreaterThan(0)),
        valid_values=[full, str(full)],
        invalid_values=[empty, folder, missing, "", "   ", "a\0b", None, 5, b"x", []],
        expected_description="size: > 0",
        rule_factory=SizeIs,
        invalid_init_params=[
            (("not callable",), {}),
            ((None,), {}),
            ((5,), {}),
        ],
        check_value=False,  # the card is the wrapped rule's, about the measured size
        verbose=False,
    )


def test_size_is_greater_than_zero_separates_empty_from_non_empty_files(tmp_path) -> None:
    empty = tmp_path / "empty.bin"
    empty.write_bytes(b"")
    full = tmp_path / "full.bin"
    full.write_bytes(b"x")
    rule = SizeIs(GreaterThan(0))
    assert rule.is_valid(empty) is False
    assert rule.is_valid(full) is True


@pytest.mark.parametrize("size, expected", [(0, False), (1, True), (4, True), (5, False)])
def test_size_is_works_with_a_range(tmp_path, size, expected) -> None:
    target = tmp_path / "a.bin"
    target.write_bytes(bytes(size))
    assert SizeIs(InRange(1, 4)).is_valid(target) is expected


def test_size_is_accepts_a_plain_callable(tmp_path) -> None:
    def at_most_three(size: int) -> bool:
        return size <= 3

    small = tmp_path / "small.bin"
    small.write_bytes(b"123")
    large = tmp_path / "large.bin"
    large.write_bytes(b"1234")
    rule = SizeIs(at_most_three)
    assert rule.is_valid(small) is True
    assert rule.is_valid(large) is False
    assert rule.describe() == "size: at_most_three"


def test_size_is_describe_uses_the_wrapped_rules_text() -> None:
    assert SizeIs(LessThan(10)).describe() == "size: < 10"
    assert SizeIs(InRange(1, 4)).describe() == "size: in [1, 4]"


def test_size_is_describe_wraps_compound_operands_in_parentheses() -> None:
    assert SizeIs(GreaterThan(5) | LessThan(2)).describe() == "size: (> 5 | < 2)"


def test_size_is_a_directory_and_a_missing_path_fail(tmp_path) -> None:
    rule = SizeIs(GreaterThan(-1))
    assert rule.is_valid(tmp_path) is False
    assert rule.is_valid(tmp_path / "missing") is False


def test_size_is_follows_a_symlink_to_a_file(tmp_path, symlink_or_skip) -> None:
    target = tmp_path / "target.bin"
    target.write_bytes(b"12345")
    link = tmp_path / "link.bin"
    symlink_or_skip(link, target)
    assert SizeIs(GreaterThan(4)).is_valid(link) is True


def test_size_is_negation_also_accepts_what_has_no_size(tmp_path) -> None:
    """A path without a size fails the plain rule, so its negation passes — combine with IsFile() when that matters."""
    rule = ~SizeIs(GreaterThan(0))
    assert rule.is_valid(tmp_path / "missing") is True
    assert (IsFile() & rule).is_valid(tmp_path / "missing") is False


def test_size_is_combines_with_other_rules_and_describes_readably() -> None:
    assert (IsFile() & SizeIs(GreaterThan(0))).describe() == "existing file & size: > 0"


def test_size_is_works_as_a_scanner_include_filter(tmp_path) -> None:
    (tmp_path / "full.txt").write_bytes(b"x")
    (tmp_path / "empty.txt").write_bytes(b"")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "deep.txt").write_bytes(b"xy")
    result = collect_paths(tmp_path, include_filter=SizeIs(GreaterThan(0)))
    assert sorted(p.name for p in result) == ["deep.txt", "full.txt"]


def test_size_is_works_as_a_scanner_exclude_filter(tmp_path) -> None:
    (tmp_path / "big.bin").write_bytes(bytes(100))
    (tmp_path / "small.bin").write_bytes(bytes(5))
    result = collect_paths(tmp_path, exclude_filter=SizeIs(GreaterThan(10)))
    assert sorted(p.name for p in result) == ["small.bin"]


def test_size_is_exposes_the_wrapped_rule() -> None:
    inner = GreaterThan(0)
    assert SizeIs(inner).rule is inner


@pytest.mark.parametrize("bad", ["GreaterThan", None, 5, []])
def test_size_is_rejects_a_non_callable_operand(bad) -> None:
    with pytest.raises(ParamError):
        SizeIs(bad)


def test_size_is_card_is_the_wrapped_rules_own_for_the_size(subtests, tmp_path) -> None:
    big = tmp_path / "big.bin"
    big.write_bytes(bytes(50))
    assert_exception_function(
        subtests,
        func=SizeIs(LessThan(10)).validate,
        invalid_params=(big, Kwargs(value_name="source", context="step")),
        exception_type=ValidationError,
        error_name="LESS_THAN_ERROR",
        label="source.size",
        context="step",
        value=50,
        expected="value less than 10",
        problem="Value 50 is not less than 10.",
        exception=ValueError,
        verbose=False,
    )


def test_size_is_card_for_a_path_without_a_size(subtests, tmp_path) -> None:
    missing = tmp_path / "missing.bin"
    assert_exception_function(
        subtests,
        func=SizeIs(GreaterThan(0)).validate,
        invalid_params=(missing, Kwargs(value_name="source", context="step")),
        exception_type=ValidationError,
        error_name="FILE_SIZE_IS_ERROR",
        label="source",
        context="step",
        value=missing,
        expected="a file whose size: > 0",
        problem=(
            f"The size of {missing!r} cannot be read "
            "(it is missing, is not a regular file, is unreadable, or does not decode)."
        ),
        how_to_fix="Provide a path to an existing, readable file.",
        exception=ValueError,
        verbose=False,
    )


def test_size_is_card_for_a_non_path(subtests) -> None:
    assert_exception_function(
        subtests,
        func=SizeIs(GreaterThan(0)).validate,
        invalid_params=(5, Kwargs(value_name="source")),
        exception_type=ValidationError,
        error_name="FILE_SIZE_IS_ERROR",
        label="source",
        value=5,
        problem="Value 5 of type 'int' is not a string or Path.",
        how_to_fix="Provide a path as a str or a Path object.",
        exception=TypeError,
        verbose=False,
    )


def test_size_is_card_for_a_blank_string(subtests) -> None:
    assert_exception_function(
        subtests,
        func=SizeIs(GreaterThan(0)).validate,
        invalid_params=("",),
        exception_type=ValidationError,
        error_name="FILE_SIZE_IS_ERROR",
        value="",
        problem="Value '' cannot be used as a path (it is blank or contains a null byte).",
        exception=ValueError,
        verbose=False,
    )
