"""Shared test support: platform markers and fixtures for what only some systems can do.

Markers (a reason in the marker makes the `-rs` summary readable):

    @pytest.mark.posix_only("permission bits")      # skipped on Windows
    @pytest.mark.windows_only("locked files")       # skipped everywhere else
    @pytest.mark.revocable_permissions              # needs chmod to really take access away

Fixtures:

    symlink_or_skip(link, target, *, directory=False)   # skips where symlinks cannot be created
    hardlink_or_skip(source, alias)                     # skips where hard links cannot be created
    lock_file(path)                                     # Windows only: a context manager that holds a file exclusively
"""

import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
import pytest

IS_WINDOWS = os.name == "nt"
IS_ROOT = hasattr(os, "geteuid") and os.geteuid() == 0


# ----------------------------------------------------------------------
# Markers
# ----------------------------------------------------------------------

def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "posix_only(reason): skipped on Windows")
    config.addinivalue_line("markers", "windows_only(reason): skipped on every system but Windows")
    config.addinivalue_line("markers", "revocable_permissions: needs chmod to really take access away")


def _skip(item: pytest.Item, text: str) -> None:
    item.add_marker(pytest.mark.skip(reason=text))


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        posix = item.get_closest_marker("posix_only")
        if posix and IS_WINDOWS:
            detail = f": {posix.args[0]}" if posix.args else ""
            _skip(item, f"POSIX only{detail}")

        windows = item.get_closest_marker("windows_only")
        if windows and not IS_WINDOWS:
            detail = f": {windows.args[0]}" if windows.args else ""
            _skip(item, f"Windows only{detail}")

        if item.get_closest_marker("revocable_permissions"):
            if IS_WINDOWS:
                _skip(item, "Windows: permission bits cannot make a file unreadable (see rules/test_windows_rules.py)")
            elif IS_ROOT:
                _skip(item, "Running as root: permission bits do not apply")


# ----------------------------------------------------------------------
# Links
# ----------------------------------------------------------------------

@pytest.fixture
def symlink_or_skip() -> Callable[..., None]:
    """Create a symlink, or skip the test where that is not allowed (Windows without Developer Mode)."""

    def create(link: Path, target: Path | str, *, directory: bool = False) -> None:
        try:
            link.symlink_to(target, target_is_directory=directory)
        except (OSError, NotImplementedError):
            pytest.skip("Symlinks are not available here (on Windows turn on Developer Mode).")

    return create


@pytest.fixture
def hardlink_or_skip() -> Callable[..., None]:
    """Create a hard link, or skip the test where the filesystem does not support it."""

    def create(source: Path, alias: Path) -> None:
        try:
            os.link(source, alias)
        except (OSError, NotImplementedError):
            pytest.skip("Hard links are not available here.")

    return create


# ----------------------------------------------------------------------
# Locked files (Windows)
# ----------------------------------------------------------------------

@pytest.fixture
def lock_file() -> Callable[[Path], object]:
    """Windows only: `with lock_file(path):` holds the file with no sharing at all.

    While the block runs, any other open, rename or delete of that file fails with a sharing
    violation — what an antivirus scanner or another program does to a file in real life.
    """
    if not IS_WINDOWS:
        pytest.skip("Windows only: file locking by share mode.")

    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateFileW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    ]
    kernel32.CreateFileW.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    generic_read, open_existing, file_attribute_normal = 0x80000000, 3, 0x80
    invalid_handle = ctypes.c_void_p(-1).value

    @contextmanager
    def lock(path: Path) -> Iterator[None]:
        # share mode 0: nobody else may read, write or delete the file while it is held
        handle = kernel32.CreateFileW(str(path), generic_read, 0, None, open_existing, file_attribute_normal, None)
        if handle is None or handle == invalid_handle:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            yield
        finally:
            kernel32.CloseHandle(handle)

    return lock
