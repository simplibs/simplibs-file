import hashlib
from pathlib import Path
from typing import get_args
import pytest
from simplibs.exception import AccessError, NotFoundError, StateError
from simplibs.file.annotations import HashAlgorithm
from simplibs.file.logic.inspection import file_hash


def _write(path: Path, data: bytes) -> Path:
    path.write_bytes(data)
    return path


# ----------------------------------------------------------------------
# Correctness against hashlib
# ----------------------------------------------------------------------

def test_file_hash_default_is_sha256_lowercase_hex(tmp_path: Path) -> None:
    """Without arguments the digest is SHA-256 as lowercase hexadecimal text."""
    file = _write(tmp_path / "a.bin", b"abc")

    digest = file_hash(file)

    assert digest == hashlib.sha256(b"abc").hexdigest()
    assert digest == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert digest == digest.lower()


@pytest.mark.parametrize("algorithm", get_args(HashAlgorithm))
def test_file_hash_matches_hashlib_for_every_algorithm(tmp_path: Path, algorithm) -> None:
    """Every supported algorithm agrees with hashlib on the same content."""
    data = bytes(range(256)) * 20
    file = _write(tmp_path / "a.bin", data)

    expected = hashlib.new(algorithm, data, usedforsecurity=False).hexdigest()

    assert file_hash(file, algorithm=algorithm) == expected


def test_file_hash_of_empty_file_is_the_known_empty_digest(tmp_path: Path) -> None:
    """The empty file has the well-known digests."""
    file = _write(tmp_path / "empty.bin", b"")

    assert file_hash(file) == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert file_hash(file, algorithm="md5") == "d41d8cd98f00b204e9800998ecf8427e"
    assert file_hash(file, algorithm="sha1") == "da39a3ee5e6b4b0d3255bfef95601890afd80709"


@pytest.mark.parametrize("chunk_size", [1, 3, 9, 10, 11, 4096, 1_048_576])
def test_file_hash_is_independent_of_chunk_size(tmp_path: Path, chunk_size) -> None:
    """Chunk boundaries smaller than, equal to and larger than the file give the same digest."""
    data = b"0123456789"
    file = _write(tmp_path / "a.bin", data)

    assert file_hash(file, chunk_size=chunk_size) == hashlib.sha256(data).hexdigest()


def test_file_hash_of_multi_megabyte_file_spans_several_default_chunks(tmp_path: Path) -> None:
    """A file larger than the default 1 MiB chunk is hashed whole."""
    data = bytes(range(256)) * 12_000  # about 3 MB
    file = _write(tmp_path / "big.bin", data)

    assert file_hash(file) == hashlib.sha256(data).hexdigest()


def test_file_hash_changes_with_one_byte(tmp_path: Path) -> None:
    """A single changed byte changes the digest."""
    first = _write(tmp_path / "first.bin", b"hello world")
    second = _write(tmp_path / "second.bin", b"hello_world")

    assert file_hash(first) != file_hash(second)


def test_file_hash_ignores_path_and_metadata(tmp_path: Path) -> None:
    """Two identical files in different folders hash equal."""
    (tmp_path / "one").mkdir()
    (tmp_path / "two").mkdir()
    first = _write(tmp_path / "one" / "a.bin", b"same")
    second = _write(tmp_path / "two" / "different-name.dat", b"same")

    assert file_hash(first) == file_hash(second)


def test_file_hash_accepts_string_path(tmp_path: Path) -> None:
    """A str path works like a Path."""
    file = _write(tmp_path / "a.bin", b"abc")

    assert file_hash(str(file)) == file_hash(file)


def test_file_hash_follows_symlink(tmp_path: Path) -> None:
    """A symlink is followed, the CONTENT is hashed."""
    real = _write(tmp_path / "real.bin", b"content")
    link = tmp_path / "link.bin"
    try:
        link.symlink_to(real)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available here")

    assert file_hash(link) == file_hash(real)


# ----------------------------------------------------------------------
# FIPS honesty
# ----------------------------------------------------------------------

@pytest.mark.parametrize(
    "algorithm, expected_flag",
    [("md5", False), ("sha1", False), ("sha256", True), ("sha3_256", True), ("blake2b", True)],
)
def test_file_hash_declares_legacy_algorithms_as_not_for_security(
    tmp_path: Path, monkeypatch, algorithm, expected_flag,
) -> None:
    """md5 and sha1 are declared usedforsecurity=False, so they also work on FIPS-restricted systems."""
    file = _write(tmp_path / "a.bin", b"abc")
    real_new = hashlib.new
    calls: list[tuple] = []

    def recording_new(name, *args, **kwargs):
        calls.append((name, kwargs))
        return real_new(name, *args, **kwargs)

    monkeypatch.setattr(hashlib, "new", recording_new)

    file_hash(file, algorithm=algorithm)

    assert calls == [(algorithm, {"usedforsecurity": expected_flag})]


# ----------------------------------------------------------------------
# Failures
# ----------------------------------------------------------------------

def test_file_hash_missing_file_raises_not_found(tmp_path: Path) -> None:
    """A missing file is NotFoundError."""
    with pytest.raises(NotFoundError) as info:
        file_hash(tmp_path / "missing.bin")

    assert info.value.error_name == "FILE_HASH_NOT_FOUND"


def test_file_hash_directory_raises_state_error(tmp_path: Path) -> None:
    """A directory cannot be hashed."""
    with pytest.raises(StateError) as info:
        file_hash(tmp_path)

    assert info.value.error_name == "FILE_HASH_NOT_A_FILE"


def test_file_hash_refused_read_is_access_error(tmp_path: Path, monkeypatch) -> None:
    """When the OS refuses to open the file, an AccessError card is raised."""
    file = _write(tmp_path / "locked.bin", b"abc")
    original_open = Path.open

    def refusing_open(self, *args, **kwargs):
        if self.name == "locked.bin":
            raise PermissionError("denied")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", refusing_open)

    with pytest.raises(AccessError) as info:
        file_hash(file)

    assert info.value.error_name == "FILE_HASH_FAILED"
    assert isinstance(info.value, PermissionError)
