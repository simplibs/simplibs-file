from typing import Any, Callable
from simplibs.exception import ValidationError
from simplibs.path.tools import to_path, build_not_a_path_exception, build_path_rule_exception
from simplibs.rules import AllOf, AnyOf, Compose, Rule, UserRule
# Outers
from .._validations import raise_rule_param_invalid_error


class FilePartIs(Rule):
    """Base of the rules that judge one measurable part of a FILE with another rule.

    A subclass names the part (`_part_name`) and reads it from the disk
    (`_read_part`); everything else — validation, evaluation, description,
    failure card — is shared. Not meant to be used directly.
    """

    __slots__ = ("rule",)

    _part_name: str = "part"

    # ----------------------------------------------------------------------
    # Part reading (the one thing a subclass defines)
    # ----------------------------------------------------------------------
    def _read_part(self, path) -> Any:
        """Return the part, or `None` if it cannot be read. Must never raise."""
        raise NotImplementedError

    # ----------------------------------------------------------------------
    # Constructor initialization
    # ----------------------------------------------------------------------
    def __init__(self, rule: Rule | Callable[[Any], bool]) -> None:

        # 1. Parameter validation
        if not callable(rule):
            raise_rule_param_invalid_error(
                type(self).__name__,
                "rule",
                rule,
                "a Rule or a callable taking one argument",
                exception=TypeError,
            )

        # 2. A plain callable gets the missing Rule contract (describe, build_exception)
        self.rule = rule if isinstance(rule, Rule) else UserRule(rule)

    # ----------------------------------------------------------------------
    # Rule definition
    # ----------------------------------------------------------------------
    def is_valid(self, value: Any) -> bool:

        # 1. Anything that cannot be turned into a path fails
        path = to_path(value)
        if path is None:
            return False

        # 2. A part that cannot be read (missing file, a directory, no permission, bad bytes) fails
        part = self._read_part(path)
        if part is None:
            return False

        # 3. Let the wrapped rule judge the part
        return bool(self.rule.is_valid(part))

    # ----------------------------------------------------------------------
    # Description definition
    # ----------------------------------------------------------------------
    def describe(self) -> str:

        # 1. The wrapped rule describes itself — a faulty describe() must never break this one
        # noinspection PyBroadException
        try:
            text = self.rule.describe()
        except Exception:
            text = None
        if not isinstance(text, str) or not text:
            text = type(self.rule).__name__

        # 2. A compound operand needs parentheses so the prefix reads as covering all of it
        if isinstance(self.rule, (AllOf, AnyOf, Compose)):
            text = f"({text})"

        # 3. "name: <rule>"
        return f"{self._part_name}: {text}"

    # ----------------------------------------------------------------------
    # Exception definition
    # ----------------------------------------------------------------------
    def build_exception(
        self,
        value: Any,
        value_name: str | None = None,
        context: str | None = None,
    ) -> Exception:

        # 1. Prepare data
        error_name = f"FILE_{self._part_name.upper().replace(' ', '_')}_IS_ERROR"
        expected = f"a file whose {self.describe()}"

        # 2. Not a usable path at all
        path = to_path(value)
        if path is None:
            return build_not_a_path_exception(
                error_name=error_name,
                expected=expected,
                value=value,
                value_name=value_name,
                context=context,
            )

        # 3. A usable path, but the part cannot be read
        part = self._read_part(path)
        if part is None:
            return build_path_rule_exception(
                error_name=error_name,
                expected=expected,
                value=value,
                value_name=value_name,
                context=context,
                problem=f"The {self._part_name} of {value!r} cannot be read (it is missing, is not a regular file, is unreadable, or does not decode).",
                how_to_fix="Provide a path to an existing, readable file.",
            )

        # 4. The part fails the wrapped rule — vend the wrapped rule's own card
        if not self.rule.is_valid(part):
            label = f"{value_name}.{self._part_name}" if value_name else self._part_name
            return self.rule.build_exception(part, value_name=label, context=context)

        # 5. Fallback (the part unexpectedly passed during error construction)
        return ValidationError(
            error_name=f"{error_name}_UNREACHABLE",
            label=value_name,
            expected=expected,
            value=value,
            problem="The file part unexpectedly passed during error construction.",
            context=context,
            how_to_fix=("Check validation logic state.",),
            exception=RuntimeError,
        )


_DESIGN_NOTES = """
# FilePartIs — a Lens From a File to One of Its Measurable Parts

## Purpose
`SizeIs(GreaterThan(0))` and `ContentIs(StartsWith("#!"))` need no new
comparison or string logic: every numeric and string rule already exists. These
lenses only point them at the right piece of the file — its size, or the
beginning of its text. This base holds everything else.

## Sibling of `PathPartIs` — and Why It Is Not a Subclass
`PathPartIs` (in `simplibs-path`) extracts a part from the path TEXT, which
cannot fail. A file part comes from the disk, which can: the file may be
missing, a directory, unreadable, or not decodable. So `_read_part` may answer
`None` ("no part"), and the two places that care react differently:
* `is_valid` -> `False`, never an exception;
* `build_exception` -> a card that says the part could not be read, instead of
  asking the wrapped rule to judge nothing.
Neither the size (an `int`) nor the text (a `str`) can legitimately be `None`,
so `None` is an unambiguous marker.

## The Failure Card Is the Wrapped Rule's Own
Same principle as `PathPartIs` / `AllOf` / `ForEach`: `SizeIs(LessThan(10))` on
a 50-byte file reports that `50` is not `< 10`, labelled `source.size`.
`exc.value` is therefore the part, not the path.

## TODO(test)
Rule judged twice (once in `is_valid`, once in `build_exception`) while the file
changes in between -> the "unreachable" fallback card.
Contract tests must use `check_value=False`, as for `PathPartIs`.
"""
