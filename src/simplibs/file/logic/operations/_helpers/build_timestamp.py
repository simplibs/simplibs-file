from datetime import datetime


def build_timestamp(now: datetime | None = None) -> str:
    """Format a moment as a `YYYYMMDD_HHMMSS` string for file names.

    Args:
        now: The moment to format; the current local time when omitted.

    Returns:
        A sortable, filename-safe timestamp such as `20261013_142530`.
    """

    # 1. Default to the current local time
    moment = now if now is not None else datetime.now()

    # 2. Format without separators that are illegal in file names
    return moment.strftime("%Y%m%d_%H%M%S")


_DESIGN_NOTES = """
# build_timestamp — a Testable Clock for File Names

## Purpose
`backup_file` used to call `datetime.now()` inline, which cannot be tested
without patching the clock. The optional `now` makes the format and the
default separately testable.

## Resolution Is One Second
Two backups in the same second get the same stamp — `backup_file` resolves
that with `make_unique_path`, not with a finer clock.
"""
