from .ContentIs import ContentIs
from .IsTextFile import IsTextFile
from .SizeIs import SizeIs

__all__ = [
    "ContentIs",
    "IsTextFile",
    "SizeIs",
]


_DESIGN_NOTES = """
# simplibs.file.rules — Rules Over Files

## Purpose
Filters for pipelines and `validate(...)`: `IsTextFile` (what kind of file),
`SizeIs` (how big) and `ContentIs` (what it starts with). Structural questions
about a PATH (`IsFile`, `HasSuffix`, `NameIs`...) live in `simplibs.path.rules`.

    from simplibs.file.rules import ContentIs, IsTextFile, SizeIs
    from simplibs.path.rules import HasSuffix, IsFile

    extractable = IsFile() & HasSuffix(".py") & IsTextFile() & SizeIs(LessThan(1_000_000))

## Domain Folder
`rules/` has its own `__all__` and is not re-exported from the package root,
exactly like `simplibs.path.rules`.

## The Two Lenses
`SizeIs` and `ContentIs` derive from `FilePartIs` (in `_helpers/`), the file-side
sibling of `simplibs-path`'s `PathPartIs`.

## Internal Components Registry

| Component   | Type     | Description                                                     |
| :---------- | :------- | :-------------------------------------------------------------- |
| `ContentIs` | Class    | Rule to judge the beginning of a file's text with another rule. |
| `IsTextFile`| Class    | Rule ensuring a path is a readable file with a text-like start. |
| `SizeIs`    | Class    | Rule to judge the size of a file in bytes with another rule.    |
"""