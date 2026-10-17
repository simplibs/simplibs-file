from typing import NoReturn
from simplibs.exception import ParamError


def raise_invalid_suffix_error(
    suffix: str,
    operation: str,
) -> NoReturn:
    """Raise ParamError when a suffix argument does not have the shape of a file suffix.

    Args:
        suffix: The rejected suffix.
        operation: A single lowercase word naming the operation ("backup", ...).
    """

    # 1. Raise structured ParamError wrapping a ValueError
    raise ParamError(
        error_name=f"FILE_{operation.upper()}_INVALID_SUFFIX",
        label="suffix",
        value=suffix,
        problem=f"{suffix!r} is not a valid suffix for the {operation}.",
        expected="An empty string, or a dot followed by at least one character, without path separators (e.g. '.bak', '.tar.gz').",
        how_to_fix=(
            "Start the suffix with a dot, e.g. '.bak'.",
            "Do not use '/', '\\' or null characters in it.",
        ),
        exception=ValueError,
    )


_DESIGN_NOTES = """
# raise_invalid_suffix_error — a Suffix That Is Not One

## Purpose
`backup_file(suffix="bak")` would build a name ending in `...txtbak`. The shape
is judged by `is_valid_suffix` of `simplibs-path` (the same definition
`change_suffix` and `HasSuffix` use); this card reports a rejection.
"""
