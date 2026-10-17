from pathlib import Path
import pytest
from simplibs.exception import ParamError, ValidationError
from simplibs.exception.testing import assert_exception_function, Kwargs
from simplibs.file.rules import ContentIs
from simplibs.path.logic.scanners import collect_paths
from simplibs.path.rules import IsFile
from simplibs.rules.predicates.comparisons import Equals
from simplibs.rules.predicates.strings import Contains, StartsWith
from simplibs.rules.testing import assert_rule_contract


def test_content_is_contract(subtests, tmp_path) -> None:
    """Verify the complete contract of the ContentIs rule."""
    script = tmp_path / "script.sh"
    script.write_bytes(b"#!/bin/sh\necho hi\n")
    bom_script = tmp_path / "bom_script.sh"
    bom_script.write_bytes(b"\xef\xbb\xbf#!/bin/sh\n")
    crlf_script = tmp_path / "crlf_script.sh"
    crlf_script.write_bytes(b"#!/bin/sh\r\necho hi\r\n")
    plain = tmp_path / "plain.txt"
    plain.write_bytes(b"echo hi\n")
    empty = tmp_path / "empty.txt"
    empty.write_bytes(b"")
    binary = tmp_path / "binary.bin"
    binary.write_bytes(b"\xff\xfe\xfa")
    folder = tmp_path / "folder"
    folder.mkdir()
    missing = tmp_path / "missing"
    ok_rule = StartsWith("#!")
    assert_rule_contract(
        subtests,
        rule=ContentIs(ok_rule),
        valid_values=[script, str(bom_script), crlf_script],
        invalid_values=[plain, empty, binary, folder, missing, "", "   ", "a\0b", None, 5, b"x", []],
        expected_description="content: string starting with '#!'",
        rule_factory=ContentIs,
        invalid_init_params=[
            (("not callable",), {}),
            ((None,), {}),
            ((5,), {}),
            ((ok_rule,), {"encoding": "rot13"}),
            ((ok_rule,), {"encoding": ""}),
            ((ok_rule,), {"encoding": 5}),
            ((ok_rule,), {"encoding": None}),
            ((ok_rule,), {"max_bytes": 0}),
            ((ok_rule,), {"max_bytes": -1}),
            ((ok_rule,), {"max_bytes": True}),
            ((ok_rule,), {"max_bytes": "x"}),
            ((ok_rule,), {"max_bytes": 1.5}),
        ],
        check_value=False,  # the card is the wrapped rule's, about the decoded head
        verbose=False,
    )


def test_content_is_stores_its_defaults_and_the_wrapped_rule() -> None:
    inner = StartsWith("#!")
    rule = ContentIs(inner)
    assert rule.rule is inner
    assert rule.encoding == "utf-8-sig"
    assert rule.max_bytes == 65_536


def test_content_is_stores_custom_parameters() -> None:
    rule = ContentIs(StartsWith("x"), encoding="cp1250", max_bytes=10)
    assert rule.encoding == "cp1250"
    assert rule.max_bytes == 10


def test_content_is_parameters_after_the_rule_are_keyword_only() -> None:
    with pytest.raises(TypeError):
        ContentIs(StartsWith("x"), "utf-8")


@pytest.mark.parametrize("bad", ["rot13", "", "   ", 5, None])
def test_content_is_rejects_an_invalid_encoding(bad) -> None:
    with pytest.raises(ParamError) as info:
        ContentIs(StartsWith("x"), encoding=bad)
    assert info.value.exception is ValueError


@pytest.mark.parametrize("bad", [0, -1, True, "x", 1.5, None])
def test_content_is_rejects_an_invalid_max_bytes(bad) -> None:
    with pytest.raises(ParamError) as info:
        ContentIs(StartsWith("x"), max_bytes=bad)
    assert info.value.exception is ValueError


@pytest.mark.parametrize("bad", ["StartsWith", None, 5, []])
def test_content_is_rejects_a_non_callable_operand_as_a_type_error(bad) -> None:
    with pytest.raises(ParamError) as info:
        ContentIs(bad)
    assert info.value.exception is TypeError


def test_content_is_sees_only_the_beginning_of_the_file(tmp_path) -> None:
    target = tmp_path / "big.txt"
    target.write_bytes(b"x" * 100 + b"TODO")
    assert ContentIs(Contains("TODO"), max_bytes=50).is_valid(target) is False
    assert ContentIs(Contains("TODO"), max_bytes=200).is_valid(target) is True


def test_content_is_a_character_cut_by_max_bytes_is_not_an_error(tmp_path) -> None:
    target = tmp_path / "a.txt"
    target.write_bytes("ač".encode("utf-8"))   # b"a\xc4\x8d"
    assert ContentIs(Equals("a"), max_bytes=2).is_valid(target) is True


def test_content_is_a_bom_is_removed_by_default(tmp_path) -> None:
    target = tmp_path / "a.sh"
    target.write_bytes(b"\xef\xbb\xbf#!/bin/sh\n")
    assert ContentIs(StartsWith("#!")).is_valid(target) is True
    assert ContentIs(StartsWith("#!"), encoding="utf-8").is_valid(target) is False


@pytest.mark.parametrize("raw", [b"a\r\nb", b"a\rb", b"a\nb"])
def test_content_is_line_endings_are_normalized(tmp_path, raw) -> None:
    target = tmp_path / "a.txt"
    target.write_bytes(raw)
    assert ContentIs(Equals("a\nb")).is_valid(target) is True


def test_content_is_an_empty_file_has_empty_content(tmp_path) -> None:
    target = tmp_path / "empty.txt"
    target.write_bytes(b"")
    assert ContentIs(Equals("")).is_valid(target) is True
    assert ContentIs(StartsWith("x")).is_valid(target) is False


def test_content_is_undecodable_bytes_fail_even_for_a_rule_that_accepts_anything(tmp_path) -> None:
    target = tmp_path / "binary.bin"
    target.write_bytes(b"\xff\xfe\xfa")
    assert ContentIs(lambda text: True).is_valid(target) is False


def test_content_is_uses_the_given_encoding(tmp_path) -> None:
    target = tmp_path / "a.txt"
    target.write_bytes("č".encode("cp1250"))
    assert ContentIs(Equals("č"), encoding="cp1250").is_valid(target) is True
    assert ContentIs(Equals("č")).is_valid(target) is False  # not valid utf-8


def test_content_is_accepts_a_plain_callable(tmp_path) -> None:
    def mentions_todo(text: str) -> bool:
        return "TODO" in text

    target = tmp_path / "a.py"
    target.write_text("# TODO: later\n")
    rule = ContentIs(mentions_todo)
    assert rule.is_valid(target) is True
    assert rule.describe() == "content: mentions_todo"


def test_content_is_a_directory_and_a_missing_path_fail(tmp_path) -> None:
    rule = ContentIs(lambda text: True)
    assert rule.is_valid(tmp_path) is False
    assert rule.is_valid(tmp_path / "missing") is False


def test_content_is_describe_uses_the_wrapped_rules_text() -> None:
    assert ContentIs(Contains("TODO")).describe() == "content: string containing 'TODO'"


def test_content_is_describe_wraps_compound_operands_in_parentheses() -> None:
    rule = ContentIs(Contains("a") | Contains("b"))
    assert rule.describe() == "content: (string containing 'a' | string containing 'b')"


def test_content_is_combines_with_other_rules_and_describes_readably() -> None:
    rule = IsFile() & ContentIs(StartsWith("#!"))
    assert rule.describe() == "existing file & content: string starting with '#!'"


def test_content_is_works_as_a_scanner_include_filter(tmp_path) -> None:
    (tmp_path / "run.sh").write_bytes(b"#!/bin/sh\n")
    (tmp_path / "notes.txt").write_bytes(b"hello\n")
    (tmp_path / "image.bin").write_bytes(b"\xff\xfe\xfa")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "tool.py").write_bytes(b"#!/usr/bin/env python\n")
    result = collect_paths(tmp_path, include_filter=ContentIs(StartsWith("#!")))
    assert sorted(p.name for p in result) == ["run.sh", "tool.py"]


def test_content_is_card_is_the_wrapped_rules_own_for_the_content(subtests, tmp_path) -> None:
    target = tmp_path / "a.txt"
    target.write_text("hello")
    assert_exception_function(
        subtests,
        func=ContentIs(StartsWith("#!")).validate,
        invalid_params=(target, Kwargs(value_name="source", context="step")),
        exception_type=ValidationError,
        error_name="STARTS_WITH_ERROR",
        label="source.content",
        context="step",
        value="hello",
        expected="string starting with '#!'",
        problem="Value 'hello' does not start with '#!'.",
        exception=ValueError,
        verbose=False,
    )


def test_content_is_card_for_a_file_that_cannot_be_decoded(subtests, tmp_path) -> None:
    binary = tmp_path / "binary.bin"
    binary.write_bytes(b"\xff\xfe\xfa")
    assert_exception_function(
        subtests,
        func=ContentIs(StartsWith("#!")).validate,
        invalid_params=(binary, Kwargs(value_name="source", context="step")),
        exception_type=ValidationError,
        error_name="FILE_CONTENT_IS_ERROR",
        label="source",
        context="step",
        value=binary,
        expected="a file whose content: string starting with '#!'",
        problem=(
            f"The content of {binary!r} cannot be read "
            "(it is missing, is not a regular file, is unreadable, or does not decode)."
        ),
        how_to_fix="Provide a path to an existing, readable file.",
        exception=ValueError,
        verbose=False,
    )


def test_content_is_card_for_a_non_path(subtests) -> None:
    assert_exception_function(
        subtests,
        func=ContentIs(StartsWith("#!")).validate,
        invalid_params=(5, Kwargs(value_name="source")),
        exception_type=ValidationError,
        error_name="FILE_CONTENT_IS_ERROR",
        label="source",
        value=5,
        problem="Value 5 of type 'int' is not a string or Path.",
        how_to_fix="Provide a path as a str or a Path object.",
        exception=TypeError,
        verbose=False,
    )


def test_content_is_card_for_a_blank_string(subtests) -> None:
    assert_exception_function(
        subtests,
        func=ContentIs(StartsWith("#!")).validate,
        invalid_params=("",),
        exception_type=ValidationError,
        error_name="FILE_CONTENT_IS_ERROR",
        value="",
        problem="Value '' cannot be used as a path (it is blank or contains a null byte).",
        exception=ValueError,
        verbose=False,
    )
