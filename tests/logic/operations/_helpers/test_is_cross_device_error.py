import errno
import pytest
from simplibs.file.logic.operations._helpers import is_cross_device_error


def test_is_cross_device_error_recognizes_exdev() -> None:
    """The POSIX "invalid cross-device link"."""
    assert is_cross_device_error(OSError(errno.EXDEV, "Invalid cross-device link")) is True


def test_is_cross_device_error_recognizes_windows_error_17() -> None:
    """ERROR_NOT_SAME_DEVICE, which Python may leave unmapped."""
    caught_exc = OSError(errno.EINVAL, "The system cannot move the file to a different disk drive")
    caught_exc.winerror = 17

    assert is_cross_device_error(caught_exc) is True


def test_is_cross_device_error_exdev_counts_for_any_subclass() -> None:
    """The errno decides, not the class."""
    assert is_cross_device_error(PermissionError(errno.EXDEV, "x")) is True


@pytest.mark.parametrize(
    "caught_exc",
    [
        OSError(errno.EACCES, "denied"),
        OSError(errno.ENOENT, "missing"),
        OSError(errno.ENOSPC, "no space"),
        OSError(errno.EEXIST, "exists"),
        PermissionError("denied"),
        FileNotFoundError("missing"),
        IsADirectoryError("dir"),
        OSError("plain message, no errno"),
    ],
)
def test_is_cross_device_error_rejects_other_errors(caught_exc) -> None:
    """Every other failure is a real failure of the move."""
    assert is_cross_device_error(caught_exc) is False


def test_is_cross_device_error_other_windows_error_is_not_cross_device() -> None:
    """Only winerror 17 means a different device."""
    caught_exc = OSError(errno.EACCES, "denied")
    caught_exc.winerror = 5

    assert is_cross_device_error(caught_exc) is False
