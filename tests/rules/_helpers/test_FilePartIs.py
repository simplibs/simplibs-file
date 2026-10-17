from pathlib import Path
import pytest
from simplibs.exception import ParamError, ValidationError
from simplibs.exception.testing import assert_exception_function, Kwargs
from simplibs.file.rules._helpers import FilePartIs
from simplibs.rules import Rule
from simplibs.rules.predicates.comparisons import Equals, GreaterThan, LessThan
from simplibs.rules.testing import assert_rule_contract


class _Length(FilePartIs):
    """A minimal lens for the tests: the size of a regular file, None otherwise."""
    __slots__ = ()
    _part_name = "length"

    def _read_part(self, path):
        return path.stat().st_size if path.is_file() else None


class _HeadText(FilePartIs):
    """A lens whose part name has a space, to check how the error name is derived."""
    __slots__ = ()
    _part_name = "head text"

    def _read_part(self, path):
        return path.read_text() if path.is_file() else None


def test_filepartis_contract(subtests, tmp_path) -> None:
    """Verify the complete contract of a minimal FilePartIs subclass."""
    full = tmp_path / "full.bin"
    full.write_bytes(b"12345")
    empty = tmp_path / "empty.bin"
    empty.write_bytes(b"")
    folder = tmp_path / "folder"
    folder.mkdir()
    assert_rule_contract(
        subtests,
        rule=_Length(GreaterThan(0)),
        valid_values=[full, str(full)],
        invalid_values=[empty, folder, tmp_path / "missing", "", "   ", "a\0b", None, 5, b"x", []],
        expected_description="length: > 0",
        rule_factory=_Length,
        invalid_init_params=[
            (("not callable",), {}),
            ((None,), {}),
            ((5,), {}),
        ],
        check_value=False,  # the card is the wrapped rule's, about the part
        verbose=False,
    )


def test_the_base_class_requires_a_subclass_to_read_the_part() -> None:
    with pytest.raises(NotImplementedError):
        FilePartIs(GreaterThan(0))._read_part(Path("a"))


def test_a_plain_callable_is_wrapped_into_a_rule(tmp_path) -> None:
    def positive(size) -> bool:
        return size > 0

    target = tmp_path / "a.bin"
    target.write_bytes(b"x")
    rule = _Length(positive)
    assert isinstance(rule.rule, Rule)
    assert rule.is_valid(target) is True
    assert rule.describe() == "length: positive"


def test_a_rule_operand_is_kept_as_it_is() -> None:
    inner = GreaterThan(0)
    assert _Length(inner).rule is inner


@pytest.mark.parametrize("bad", ["text", None, 5, []])
def test_a_non_callable_operand_is_a_param_error_wrapping_a_type_error(bad) -> None:
    with pytest.raises(ParamError) as info:
        _Length(bad)
    assert info.value.exception is TypeError


def test_instances_have_no_dict() -> None:
    assert not hasattr(_Length(GreaterThan(0)), "__dict__")


def test_a_zero_part_is_a_real_part_not_a_missing_one(tmp_path) -> None:
    empty = tmp_path / "empty.bin"
    empty.write_bytes(b"")
    assert _Length(Equals(0)).is_valid(empty) is True


def test_an_unreadable_part_fails_without_asking_the_wrapped_rule(tmp_path) -> None:
    calls = []

    def accept_everything(part) -> bool:
        calls.append(part)
        return True

    rule = _Length(accept_everything)
    assert rule.is_valid(tmp_path / "missing") is False
    assert rule.is_valid(tmp_path) is False
    assert calls == []


def test_the_answer_of_the_wrapped_rule_is_a_strict_bool(tmp_path) -> None:
    target = tmp_path / "a.bin"
    target.write_bytes(b"x")
    assert _Length(lambda size: 7).is_valid(target) is True
    assert _Length(lambda size: 0).is_valid(target) is False


@pytest.mark.parametrize("value", [None, 5, b"x", [], "", "   ", "a\0b"])
def test_a_value_that_is_not_a_path_fails_without_raising(value) -> None:
    assert _Length(GreaterThan(0)).is_valid(value) is False


def test_describe_wraps_compound_operands_in_parentheses() -> None:
    assert _Length(GreaterThan(5) | LessThan(2)).describe() == "length: (> 5 | < 2)"
    assert _Length(GreaterThan(0) & LessThan(10)).describe() == "length: (> 0 & < 10)"


def test_a_faulty_describe_of_the_operand_falls_back_to_its_class_name() -> None:
    class _BrokenDescribe(Rule):
        __slots__ = ()

        def is_valid(self, value) -> bool:
            return True

        def build_exception(self, value, value_name=None, context=None) -> Exception:
            return ValueError()

        def describe(self) -> str:
            raise RuntimeError("broken")

    assert _Length(_BrokenDescribe()).describe() == "length: _BrokenDescribe"


def test_an_empty_describe_of_the_operand_falls_back_to_its_class_name() -> None:
    class _EmptyDescribe(Rule):
        __slots__ = ()

        def is_valid(self, value) -> bool:
            return True

        def build_exception(self, value, value_name=None, context=None) -> Exception:
            return ValueError()

        def describe(self) -> str:
            return ""

    assert _Length(_EmptyDescribe()).describe() == "length: _EmptyDescribe"


def test_the_card_error_name_is_derived_from_the_part_name() -> None:
    assert _Length(GreaterThan(0)).build_exception(5).error_name == "FILE_LENGTH_IS_ERROR"
    assert _HeadText(Equals("x")).build_exception(5).error_name == "FILE_HEAD_TEXT_IS_ERROR"


def test_the_card_for_a_part_that_fails_is_the_wrapped_rules_own(subtests, tmp_path) -> None:
    big = tmp_path / "big.bin"
    big.write_bytes(bytes(50))
    assert_exception_function(
        subtests,
        func=_Length(LessThan(10)).validate,
        invalid_params=(big, Kwargs(value_name="source", context="step")),
        exception_type=ValidationError,
        error_name="LESS_THAN_ERROR",
        label="source.length",
        context="step",
        value=50,
        expected="value less than 10",
        problem="Value 50 is not less than 10.",
        exception=ValueError,
        verbose=False,
    )


def test_the_card_without_a_value_name_uses_the_part_name(subtests, tmp_path) -> None:
    big = tmp_path / "big.bin"
    big.write_bytes(bytes(50))
    assert_exception_function(
        subtests,
        func=_Length(LessThan(10)).validate,
        invalid_params=(big,),
        exception_type=ValidationError,
        label="length",
        value=50,
        verbose=False,
    )


def test_the_card_for_an_unreadable_part_says_so(subtests, tmp_path) -> None:
    missing = tmp_path / "missing.bin"
    assert_exception_function(
        subtests,
        func=_Length(GreaterThan(0)).validate,
        invalid_params=(missing, Kwargs(value_name="source", context="step")),
        exception_type=ValidationError,
        error_name="FILE_LENGTH_IS_ERROR",
        label="source",
        context="step",
        value=missing,
        expected="a file whose length: > 0",
        problem=(
            f"The length of {missing!r} cannot be read "
            "(it is missing, is not a regular file, is unreadable, or does not decode)."
        ),
        how_to_fix="Provide a path to an existing, readable file.",
        exception=ValueError,
        verbose=False,
    )


def test_the_card_for_a_non_path(subtests) -> None:
    assert_exception_function(
        subtests,
        func=_Length(GreaterThan(0)).validate,
        invalid_params=(5, Kwargs(value_name="source")),
        exception_type=ValidationError,
        error_name="FILE_LENGTH_IS_ERROR",
        label="source",
        value=5,
        expected="a file whose length: > 0",
        problem="Value 5 of type 'int' is not a string or Path.",
        how_to_fix="Provide a path as a str or a Path object.",
        exception=TypeError,
        verbose=False,
    )


def test_the_card_for_a_blank_string(subtests) -> None:
    assert_exception_function(
        subtests,
        func=_Length(GreaterThan(0)).validate,
        invalid_params=("",),
        exception_type=ValidationError,
        error_name="FILE_LENGTH_IS_ERROR",
        value="",
        problem="Value '' cannot be used as a path (it is blank or contains a null byte).",
        exception=ValueError,
        verbose=False,
    )


def test_unreachable_fallback_when_the_part_actually_passes(tmp_path) -> None:
    target = tmp_path / "a.bin"
    target.write_bytes(b"12345")
    exc = _Length(GreaterThan(0)).build_exception(target, value_name="source")
    assert isinstance(exc, ValidationError)
    assert exc.error_name == "FILE_LENGTH_IS_UNREACHABLE_ERROR"
    assert exc.exception is RuntimeError


def test_unreachable_fallback_when_the_file_changes_between_judging_and_the_card(tmp_path) -> None:
    """The rule says no in is_valid and yes while the card is built — the file changed in between."""
    target = tmp_path / "a.bin"
    target.write_bytes(b"12345")
    answers = iter([False, True])
    rule = _Length(lambda size: next(answers))
    assert rule.is_valid(target) is False
    exc = rule.build_exception(target, value_name="source")
    assert isinstance(exc, ValidationError)
    assert exc.error_name == "FILE_LENGTH_IS_UNREACHABLE_ERROR"
    assert exc.exception is RuntimeError
