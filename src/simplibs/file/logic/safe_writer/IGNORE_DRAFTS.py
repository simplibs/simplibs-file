from typing import Final


IGNORE_DRAFTS: Final[frozenset[str]] = frozenset({
    ".*.????????.draft",
})
"""Names of the temporary drafts `SafeFileWriter` leaves next to a target.

Glob pattern for the scanners' `ignore_names`. Opt-in:
`DEFAULT_IGNORE_NAMES | IGNORE_DRAFTS`.
"""


_DESIGN_NOTES = """
# IGNORE_DRAFTS — Do Not Collect Half-Written Files

## Purpose
A draft exists for the milliseconds of a write — or forever, after a crash.
A scan that runs in the same folder must not pick it up as a real file.

## The Pattern Is Narrow on Purpose
Drafts are named `.<name>.<8 hex>.draft`, so the pattern is
`.*.????????.draft` instead of a blanket `*.draft` that would also hide a
user's own `essay.draft`. Only a hidden name with exactly an 8-character
middle part (`.x.abcdefgh.draft`) looks like a draft; `.notes.draft` does not.

## Not in `DEFAULT_IGNORE_NAMES`
That default lives in `simplibs-path`, which knows nothing about this
library. Extend it with a union: `DEFAULT_IGNORE_NAMES | IGNORE_DRAFTS`.

## Changed From the Plan
The plan said `*.draft`; the unique draft names make the narrower pattern
possible.

## TODO(test)
Verify the pattern against names produced by `create_draft`, and against
`essay.draft`, `.notes.draft`, `.a.b.draft` (must not match).
"""
