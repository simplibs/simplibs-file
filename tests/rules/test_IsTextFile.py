import os
from pathlib import Path
import pytest
from simplibs.exception import ParamError, ValidationError
from simplibs.exception.testing import assert_exception_function, Kwargs
from simplibs.file.rules import IsTextFile
from simplibs.path.logic.scanners import collect_paths
from simplibs.path.rules import HasSuffix
from simplibs.rules.testing import assert_rule_contract


def test_is_text_file_contract(subtests, tmp_path) -> None:
    """Verify the complete contract of the IsTextFile rule."""
    text = tmp_path / "a.txt"
    text.write_bytes("Příliš žluťoučký kůň\n".encode("utf-8"))
    empty = tmp_path / "empty.txt"
    empty.write_bytes(b"")
    nul = tmp_path / "nul.bin"
    nul.write_bytes(b"abc\x00def")
    undecodable = tmp_path / "undecodable.bin"
    undecodable.write_bytes(b"\xff\xfe\xfa")
    folder = tmp_path / "folder"
    folder.mkdir()
    missing = tmp_path / "missing"
    assert_rule_contract(
        subtests,
        rule=IsTextFile(),
        valid_values=[text, str(text), empty],
        invalid_values=[nul, undecodable, folder, missing, "", "   ", "a\0b", None, 5, b"x", []],
        expected_error_name="IS_TEXT_FILE_ERROR",
        expected_description="text file",
        rule_factory=IsTextFile,
        invalid_init_params=[
            ((), {"sample_size": 0}),
            ((), {"sample_size": -1}),
            ((), {"sample_size": True}),
            ((), {"sample_size": "x"}),
            ((), {"sample_size": 1.5}),
            ((), {"sample_size": None}),
            ((), {"encoding": "rot13"}),
            ((), {"encoding": ""}),
            ((), {"encoding": 5}),
            ((), {"encoding": None}),
        ],
        verbose=False,
    )


def test_is_text_file_stores_its_defaults() -> None:
    rule = IsTextFile()
    assert rule.sample_size == 8192
    assert rule.encoding == "utf-8"


def test_is_text_file_stores_custom_parameters() -> None:
    rule = IsTextFile(sample_size=100, encoding="cp1250")
    assert rule.sample_size == 100
    assert rule.encoding == "cp1250"


def test_is_text_file_parameters_are_keyword_only() -> None:
    with pytest.raises(TypeError):
        IsTextFile(100)


@pytest.mark.parametrize("bad", [0, -1, True, "x", 1.5, None])
def test_is_text_file_rejects_an_invalid_sample_size(bad) -> None:
    with pytest.raises(ParamError) as info:
        IsTextFile(sample_size=bad)
    assert info.value.exception is ValueError


@pytest.mark.parametrize("bad", ["rot13", "", "   ", 5, None])
def test_is_text_file_rejects_an_invalid_encoding(bad) -> None:
    with pytest.raises(ParamError) as info:
        IsTextFile(encoding=bad)
    assert info.value.exception is ValueError


def test_is_text_file_description_is_fixed() -> None:
    assert IsTextFile().describe() == "text file"
    assert IsTextFile(sample_size=10, encoding="cp1250").describe() == "text file"


def test_is_text_file_an_empty_file_is_text(tmp_path) -> None:
    target = tmp_path / "empty.txt"
    target.write_bytes(b"")
    assert IsTextFile().is_valid(target) is True


def test_is_text_file_a_nul_character_means_binary(tmp_path) -> None:
    target = tmp_path / "a.bin"
    target.write_bytes(b"abc\x00def")
    assert IsTextFile().is_valid(target) is False


def test_is_text_file_utf16_needs_its_own_encoding(tmp_path) -> None:
    target = tmp_path / "a.txt"
    target.write_bytes("abc".encode("utf-16"))
    assert IsTextFile(encoding="utf-16").is_valid(target) is True
    assert IsTextFile().is_valid(target) is False


def test_is_text_file_uses_the_given_encoding(tmp_path) -> None:
    target = tmp_path / "a.txt"
    target.write_bytes("č".encode("cp1250"))
    assert IsTextFile(encoding="cp1250").is_valid(target) is True
    assert IsTextFile().is_valid(target) is False


def test_is_text_file_a_character_cut_by_sample_size_is_not_an_error(tmp_path) -> None:
    target = tmp_path / "a.txt"
    target.write_bytes("č".encode("utf-8") * 10)   # 20 bytes
    assert IsTextFile(sample_size=5).is_valid(target) is True


def test_is_text_file_judges_only_the_sample(tmp_path) -> None:
    """A heuristic: a NUL after the sample is not seen."""
    target = tmp_path / "a.bin"
    target.write_bytes(b"a" * 10 + b"\x00")
    assert IsTextFile(sample_size=5).is_valid(target) is True
    assert IsTextFile(sample_size=100).is_valid(target) is False


def test_is_text_file_a_directory_and_a_missing_path_are_not_text_files(tmp_path) -> None:
    rule = IsTextFile()
    assert rule.is_valid(tmp_path) is False
    assert rule.is_valid(tmp_path / "missing") is False


@pytest.mark.revocable_permissions
def test_is_text_file_an_unreadable_file_is_not_a_text_file(tmp_path) -> None:
    target = tmp_path / "a.txt"
    target.write_text("x")
    target.chmod(0o000)
    try:
        assert IsTextFile().is_valid(target) is False
    finally:
        target.chmod(0o600)


def test_is_text_file_combines_with_other_rules_and_describes_readably() -> None:
    assert (IsTextFile() & HasSuffix(".py")).describe() == "text file & suffix '.py'"


def test_is_text_file_works_as_a_scanner_include_filter(tmp_path) -> None:
    (tmp_path / "a.py").write_text("print(1)\n")
    (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00")
    (tmp_path / "empty.txt").write_bytes(b"")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "notes.md").write_text("# notes\n")
    result = collect_paths(tmp_path, include_filter=IsTextFile())
    assert sorted(p.name for p in result) == ["a.py", "empty.txt", "notes.md"]


def test_is_text_file_card_for_a_usable_path_that_fails(subtests, tmp_path) -> None:
    binary = tmp_path / "binary.bin"
    binary.write_bytes(b"abc\x00def")
    assert_exception_function(
        subtests,
        func=IsTextFile().validate,
        invalid_params=(binary, Kwargs(value_name="source", context="step")),
        exception_type=ValidationError,
        error_name="IS_TEXT_FILE_ERROR",
        label="source",
        context="step",
        value=binary,
        expected="a text file",
        problem=(
            f"Path {binary!r} is not a text file (it is missing, is not a regular file, is unreadable, "
            "or its beginning is binary or not valid utf-8)."
        ),
        how_to_fix="Provide a path to a readable text file encoded in utf-8.",
        exception=ValueError,
        verbose=False,
    )


def test_is_text_file_card_names_the_configured_encoding(tmp_path) -> None:
    binary = tmp_path / "binary.bin"
    binary.write_bytes(b"\x00")
    exc = IsTextFile(encoding="cp1250").build_exception(binary)
    assert "cp1250" in exc.problem
    assert "cp1250" in exc.how_to_fix


def test_is_text_file_card_for_a_non_path(subtests) -> None:
    assert_exception_function(
        subtests,
        func=IsTextFile().validate,
        invalid_params=(5, Kwargs(value_name="source")),
        exception_type=ValidationError,
        error_name="IS_TEXT_FILE_ERROR",
        label="source",
        value=5,
        expected="a text file",
        problem="Value 5 of type 'int' is not a string or Path.",
        how_to_fix="Provide a path as a str or a Path object.",
        exception=TypeError,
        verbose=False,
    )


def test_is_text_file_card_for_a_blank_string(subtests) -> None:
    assert_exception_function(
        subtests,
        func=IsTextFile().validate,
        invalid_params=("",),
        exception_type=ValidationError,
        error_name="IS_TEXT_FILE_ERROR",
        value="",
        problem="Value '' cannot be used as a path (it is blank or contains a null byte).",
        how_to_fix="Provide a non-blank path without null bytes.",
        exception=ValueError,
        verbose=False,
    )
