from collections.abc import Collection
from pathlib import Path
from simplibs.path import PathLike
from simplibs.validate import validate_call
# Outers
from ...annotations import EncodingErrors, EncodingName, NewlineMode
# Inners
from .write_text import write_text


@validate_call
def write_aggregated(
    path: PathLike,
    parts: Collection[str],
    *,
    separator: str = "\n",
    encoding: EncodingName = "utf-8",
    errors: EncodingErrors = "strict",
    newline: NewlineMode = "\n",
    trailing_newline: bool = False,
    overwrite: bool = True,
    use_draft: bool = True,
    sync: bool = False,
) -> Path:
    """Join text fragments with a separator and write them as one file.

    Meant for combining several already-extracted chunks (for example from
    separate source files) into one output.

    Args:
        path: The target file. Its folder is created if missing.
        parts: The fragments to join, in order.
        separator: Placed between consecutive fragments. Defaults to one newline.
        encoding: The text encoding.
        errors: How to treat characters the encoding cannot hold.
        newline: The line ending written for every `"\\n"` (`None` for the platform's own).
        trailing_newline: If True, one `"\\n"` is added after the last fragment. Defaults to False.
        overwrite: If False, an existing file raises instead of being replaced.
        use_draft: Atomic draft-and-swap write (default) or an in-place write.
        sync: Force the data to stable storage.

    Returns:
        The normalized target `Path`.
    """

    # 1. Join the fragments
    text = separator.join(parts)

    # 2. Optionally terminate the last one
    if trailing_newline:
        text += "\n"

    # 3. Write it
    return write_text(
        path,
        text,
        encoding=encoding,
        errors=errors,
        newline=newline,
        overwrite=overwrite,
        use_draft=use_draft,
        sync=sync,
    )


_DESIGN_NOTES = """
# write_aggregated — Many Chunks, One File

## Purpose
The step at the end of an extraction pipeline: several extracted texts become
one document. Reduced to `separator.join(parts)` + `write_text`; everything
else (draft, encoding, newline) is inherited.

## Versus `write_lines`
`write_lines` writes ONE LINE PER ITEM with line endings supplied by the
library; `write_aggregated` joins arbitrary chunks with an arbitrary separator
(`"\\n\\n"`, `"\\n---\\n"`, `""`).

## `trailing_newline=False`
The exact join is the default (the old behaviour); the flag is opt-in, unlike
`write_lines`.

## TODO(test)
* Empty `parts` -> empty file (also with `trailing_newline=True` -> a single newline; decide whether that is wanted).
* `separator=""`.
"""
