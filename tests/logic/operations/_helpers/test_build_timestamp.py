import re
from datetime import datetime, timedelta, timezone
import pytest
from simplibs.file.logic.operations._helpers import build_timestamp


@pytest.mark.parametrize(
    "moment, expected",
    [
        (datetime(2026, 10, 13, 14, 25, 30), "20261013_142530"),
        (datetime(2026, 1, 2, 3, 4, 5), "20260102_030405"),
        (datetime(1999, 12, 31, 23, 59, 59), "19991231_235959"),
        (datetime(2026, 10, 13, 0, 0, 0), "20261013_000000"),
    ],
)
def test_build_timestamp_formats_the_given_moment(moment, expected) -> None:
    """`YYYYMMDD_HHMMSS`, zero-padded."""
    assert build_timestamp(moment) == expected


def test_build_timestamp_ignores_microseconds() -> None:
    """The resolution is one second."""
    assert build_timestamp(datetime(2026, 10, 13, 14, 25, 30, 999_999)) == "20261013_142530"


def test_build_timestamp_uses_the_wall_clock_fields_of_an_aware_moment() -> None:
    """Whatever the moment says is what is printed — no conversion."""
    moment = datetime(2026, 10, 13, 14, 25, 30, tzinfo=timezone(timedelta(hours=5)))

    assert build_timestamp(moment) == "20261013_142530"


def test_build_timestamp_default_is_the_current_local_time() -> None:
    """Without an argument the stamp is `now`."""
    before = datetime.now().replace(microsecond=0)
    stamp = build_timestamp()
    after = datetime.now()

    parsed = datetime.strptime(stamp, "%Y%m%d_%H%M%S")

    assert before <= parsed <= after


def test_build_timestamp_has_a_filename_safe_shape() -> None:
    """Digits and one underscore — nothing illegal in a file name."""
    assert re.fullmatch(r"\d{8}_\d{6}", build_timestamp())


def test_build_timestamp_sorts_chronologically_as_text() -> None:
    """Sortable: string order is time order."""
    earlier = build_timestamp(datetime(2026, 10, 13, 9, 59, 59))
    later = build_timestamp(datetime(2026, 10, 13, 10, 0, 0))

    assert earlier < later
