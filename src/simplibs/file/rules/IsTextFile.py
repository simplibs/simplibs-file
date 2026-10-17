from typing import Any
from simplibs.path.tools import to_path, build_path_rule_exception
from simplibs.rules import Rule
# Outers
from ..annotations._helpers import is_byte_count, is_text_encoding
from ..logic.inspect import is_text_file
# Inners
from ._validations import raise_rule_param_invalid_error


class IsTextFile(Rule):
    """Path must be a readable file whose beginning looks like text.

    Rule:
        is_text_file(value, sample_size=..., encoding=...)

    Example:
        validate(source, IsTextFile())
        include_filter = IsTextFile() & HasSuffix(".py", ".md")
    """

    __slots__ = ("sample_size", "encoding")

    # ----------------------------------------------------------------------
    # Constructor initialization
    # ----------------------------------------------------------------------
    def __init__(self, *, sample_size: int = 8192, encoding: str = "utf-8") -> None:

        # 1. Parameter validation
        if not is_byte_count(sample_size):
            raise_rule_param_invalid_error("IsTextFile", "sample_size", sample_size, "a positive int (a number of bytes)")
        if not is_text_encoding(encoding):
            raise_rule_param_invalid_error("IsTextFile", "encoding", encoding, "the name of a text encoding (e.g. 'utf-8')")

        # 2. Parameter assignment
        self.sample_size = sample_size
        self.encoding = encoding

    # ----------------------------------------------------------------------
    # Rule definition
    # ----------------------------------------------------------------------
    def is_valid(self, value: Any) -> bool:

        # 1. Anything that cannot be turned into a path fails
        path = to_path(value)
        if path is None:
            return False

        # 2. Delegate to the plain predicate (its own validation is skipped — the input is checked)
        return is_text_file(path, sample_size=self.sample_size, encoding=self.encoding, _validate_call=False)

    # ----------------------------------------------------------------------
    # Description definition
    # ----------------------------------------------------------------------
    def describe(self) -> str:

        # 1. Fixed noun phrase
        return "text file"

    # ----------------------------------------------------------------------
    # Exception definition
    # ----------------------------------------------------------------------
    def build_exception(
        self,
        value: Any,
        value_name: str | None = None,
        context: str | None = None,
    ) -> Exception:

        # 1. Build the exception (the not-a-path branch is handled by the helper)
        return build_path_rule_exception(
            error_name="IS_TEXT_FILE_ERROR",
            expected="a text file",
            value=value,
            value_name=value_name,
            context=context,
            problem=(
                f"Path {value!r} is not a text file (it is missing, is not a regular file, is unreadable, "
                f"or its beginning is binary or not valid {self.encoding})."
            ),
            how_to_fix=f"Provide a path to a readable text file encoded in {self.encoding}.",
        )


_DESIGN_NOTES = """
# IsTextFile — Text, Not Binary

## Purpose
The first gate of an extraction pipeline: `IsTextFile() & HasSuffix(".py")`
keeps a renamed image or a compiled `.pyc` from ever reaching the decoder.

## Delegates to `is_text_file`
Same heuristic (decodes the first `sample_size` bytes, no NUL character), same
never-raising contract; the rule bypasses the function's own validation because
the input was already checked.

## Parameters
`sample_size` and `encoding` are the function's, validated here by hand
(rules are classes, not `@validate_call` functions).

## A Heuristic
A binary file with a long text-looking beginning passes. The failure card says
what was checked, so the verdict is explainable.

## Description
`describe()` returns "text file" — a short noun phrase that containers
compose into larger texts.

## TODO(test)
Invalid `sample_size` / `encoding` -> `ParamError`; non-path value -> the shared "not a path" card;
UTF-16 with `encoding="utf-16"`.
"""
