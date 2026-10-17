import errno


def is_cross_device_error(caught_exc: OSError) -> bool:
    """Check whether an OSError says "source and destination are on different devices".

    Args:
        caught_exc: The exception raised by `os.replace`.

    Returns:
        True for `EXDEV` (POSIX) and Windows error 17 (`ERROR_NOT_SAME_DEVICE`).
    """

    # 1. POSIX errno, or the Windows error code that Python may leave unmapped
    return caught_exc.errno == errno.EXDEV or getattr(caught_exc, "winerror", None) == 17


_DESIGN_NOTES = """
# is_cross_device_error — "Not on the Same Disk"

`os.replace` cannot cross filesystems (`G:` -> `C:`; `/tmp` -> `/home`). That
is not a failure of `move_file`, only a signal to copy-then-delete instead.
"""
