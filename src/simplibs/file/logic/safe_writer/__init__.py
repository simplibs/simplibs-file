from .IGNORE_DRAFTS import IGNORE_DRAFTS
from .SafeFileWriter import SafeFileWriter


_DESIGN_NOTES = """
# safe_writer — Crash-Safe Writing

`SafeFileWriter` (the context manager) and `IGNORE_DRAFTS` (the scanner
pattern for its leftovers). The three draft steps live in `_helpers/`.

Plain imports, no `__all__` — the package root decides what is public.

## Internal Components Registry

| Component       | Type            | Description                                                     |
| :-------------- | :-------------- | :-------------------------------------------------------------- |
| `SafeFileWriter`| Class           | Context manager for crash-safe file writing via draft-and-swap. |
| `IGNORE_DRAFTS` | Constant (Set)  | Scanner pattern for matching temporary leftover draft files.    |
"""