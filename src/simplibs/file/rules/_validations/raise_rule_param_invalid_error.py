from typing import Any, NoReturn
from simplibs.exception import ParamError


def raise_rule_param_invalid_error(
    rule_name: str,
    param_name: str,
    value: Any,
    expected: str,
    *,
    exception: type[Exception] = ValueError,
) -> NoReturn:
    """Raise ParamError when a rule is constructed with an unusable parameter.

    Args:
        rule_name: The rule class (`"SizeIs"`).
        param_name: The offending parameter (`"rule"`).
        value: The rejected value.
        expected: What the parameter should be, as a noun phrase.
        exception: The exception type to wrap — `TypeError` for a wrong kind, `ValueError` for a wrong value.
    """

    # 1. Raise structured ParamError
    raise ParamError(
        error_name="RULE_PARAM_INVALID",
        label=f"{rule_name} parameter '{param_name}'",
        value=value,
        problem=f"Invalid value {value!r} for parameter '{param_name}' of {rule_name}.",
        expected=expected,
        how_to_fix=f"Pass {expected} as '{param_name}'.",
        exception=exception,
    )


_DESIGN_NOTES = """
# raise_rule_param_invalid_error — One Constructor Guard for All File Rules

## Purpose
The three rules validate different parameters (a wrapped rule, a byte count,
an encoding name). The failure is always "this parameter is unusable", so one
card with a caller-supplied `expected` phrase replaces a card per parameter.

## Why Not the Annotations
Rules are classes, not `@validate_call` functions; their constructors check by
hand, like `HasSuffix` in `simplibs-path`.
"""
