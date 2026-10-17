from pathlib import Path
# Inners
from ._helpers import FilePartIs, read_file_size


class SizeIs(FilePartIs):
    """The size of a file, in bytes, must satisfy another rule.

    Rule:
        rule.is_valid(size of the file)

    Example:
        include_filter = SizeIs(GreaterThan(0))
        include_filter = IsFile() & SizeIs(InRange(1, 1_000_000))
        validate(upload, SizeIs(lambda size: size <= 5 * 1024 * 1024))
    """

    __slots__ = ()

    _part_name = "size"

    # ----------------------------------------------------------------------
    # Part reading
    # ----------------------------------------------------------------------
    def _read_part(self, path: Path) -> int | None:

        # 1. One stat — None for anything that is not a readable regular file
        return read_file_size(path)


_DESIGN_NOTES = """
# SizeIs — Select by File Size

## Purpose
"Non-empty files only", "skip anything over 1 MB" — without a single new
comparison: `SizeIs(GreaterThan(0))`, `SizeIs(LessThan(1_000_000))`,
`SizeIs(InRange(1, 1024))` reuse the numeric rules of `simplibs-rules`.

## A Lens, Not a Comparison
Everything (validation, description `size: > 0`, the failure card with the
label `source.size`) comes from `FilePartIs`; this class only says WHICH part.

## Missing or Unreadable
A path without a size (missing, a directory, no permission) fails the rule —
combine with `IsFile()` when the distinction matters.

## Strict Twin
`file_size` is the function that raises a card when there is no file.

## TODO(test)
`GreaterThan(0)` on empty and non-empty files; `InRange`; a plain callable (wrapped in `UserRule`);
a directory and a missing path -> False; the card of a failing size says `source.size`.
"""
