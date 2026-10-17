from pathlib import Path
from typing import Any, Callable
from simplibs.rules import Rule
# Outers
from ..annotations._helpers import is_byte_count, is_text_encoding
# Inners
from ._helpers import FilePartIs, read_file_head
from ._validations import raise_rule_param_invalid_error


class ContentIs(FilePartIs):
    """The beginning of a file's text must satisfy another rule.

    Rule:
        rule.is_valid(first max_bytes of the file, decoded)

    Example:
        include_filter = ContentIs(StartsWith("#!"))
        include_filter = IsFile() & ContentIs(Contains("TODO"), max_bytes=4096)
    """

    __slots__ = ("encoding", "max_bytes")

    _part_name = "content"

    # ----------------------------------------------------------------------
    # Constructor initialization
    # ----------------------------------------------------------------------
    def __init__(
        self,
        rule: Rule | Callable[[Any], bool],
        *,
        encoding: str = "utf-8-sig",
        max_bytes: int = 65_536,
    ) -> None:

        # 1. Parameter validation (the wrapped rule is validated by the base)
        if not is_text_encoding(encoding):
            raise_rule_param_invalid_error("ContentIs", "encoding", encoding, "the name of a text encoding (e.g. 'utf-8-sig')")
        if not is_byte_count(max_bytes):
            raise_rule_param_invalid_error("ContentIs", "max_bytes", max_bytes, "a positive int (a number of bytes)")

        # 2. Parameter assignment
        super().__init__(rule)
        self.encoding = encoding
        self.max_bytes = max_bytes

    # ----------------------------------------------------------------------
    # Part reading
    # ----------------------------------------------------------------------
    def _read_part(self, path: Path) -> str | None:

        # 1. Only the beginning, decoded — None if it cannot be read or decoded
        return read_file_head(path, max_bytes=self.max_bytes, encoding=self.encoding)


_DESIGN_NOTES = """
# ContentIs — Select by What a File Starts With

## Purpose
"Executable scripts" (`StartsWith("#!")`), "files that mention TODO near the
top", "files with a license header" — any string rule pointed at the content.

## Only the Beginning
The wrapped rule sees the first `max_bytes` (64 KiB by default), decoded.
A scan over thousands of files must not read each one whole. The consequence is
part of the contract: `Contains("x")` can miss an `x` after the first
`max_bytes`; `StartsWith` and header checks are unaffected. Raise `max_bytes`
when the whole content matters.

## Reading Rules
* Default encoding `utf-8-sig`, so a BOM never spoils `StartsWith`.
* A character cut at the end of the head is not an error.
* Line endings are normalized to `"\\n"`, as `read_text` does.
* Undecodable bytes -> the rule fails (no part), it does not raise.

## Description
`content: string starting with '#!'`, like the other lenses.
"""
