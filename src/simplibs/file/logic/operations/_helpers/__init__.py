from .build_timestamp import build_timestamp
from .copy_atomically import copy_atomically
from .is_cross_device_error import is_cross_device_error
from .move_across_devices import move_across_devices
from .prepare_destination import prepare_destination


_DESIGN_NOTES = """
# File Operations Internal Helpers Sub-Package

## Purpose
Internal helper routines supporting file manipulation operations (`copy_file`,
`move_file`, `backup_file`, etc.).

## Internal Components Registry

| Component             | Type     | Description                                                          |
| :-------------------- | :------- | :------------------------------------------------------------------- |
| `build_timestamp`     | Function | Formats a moment as a `YYYYMMDD_HHMMSS` timestamp string.           |
| `copy_atomically`     | Function | Copies a file via a draft file to guarantee atomicity.              |
| `is_cross_device_error`| Function | Detects whether an `OSError` indicates different devices (EXDEV).   |
| `move_across_devices` | Function | Moves a file across devices (atomic copy followed by unlinking source).|
| `prepare_destination` | Function | Validates that a source can be copied/moved onto a destination.      |
"""