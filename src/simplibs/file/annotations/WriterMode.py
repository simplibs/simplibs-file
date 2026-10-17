from typing import Literal


WriterMode = Literal["w", "wb", "a", "ab"]
"""The open modes `SafeFileWriter` supports: overwrite or append, text or binary."""


_DESIGN_NOTES = """
# WriterMode — the Four Modes That Make Sense

## Purpose
The old `mode: str` accepted `"x"` and `"r+"` and silently behaved as `"w"`.
A literal of exactly the supported modes turns that into an immediate,
readable error.

## Why Not `x`, `r+`, `+`
Exclusive creation and in-place update contradict the draft-and-swap idea
(the target is only ever replaced as a whole).
"""
