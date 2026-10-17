import asyncio
import hashlib
from pathlib import Path
import pytest
from simplibs.actions.testing import assert_action
from simplibs.exception import NotFoundError, StateError, ValidationError
from simplibs.file.actions import FileHash
from simplibs.path.annotations import PathLike


def test_file_hash_contract(subtests, tmp_path) -> None:
    """Verify the execution and construction contract of the FileHash action."""
    full = tmp_path / "a.bin"
    full.write_bytes(b"abc")
    empty = tmp_path / "empty.bin"
    empty.write_bytes(b"")
    assert_action(
        subtests,
        FileHash(),
        valid_values=[full, str(full), empty],
        expected_outputs=[
            hashlib.sha256(b"abc").hexdigest(),
            hashlib.sha256(b"abc").hexdigest(),
            hashlib.sha256(b"").hexdigest(),
        ],
        invalid_values=[5, "", tmp_path / "missing", tmp_path],
        expected_exception_type=[ValidationError, ValidationError, NotFoundError, StateError],
        expected_input_type=PathLike,
        expected_output_type=str,
        action_class=FileHash,
        invalid_init_params=[
            ((), {"algorithm": "crc32"}),
            ((), {"algorithm": "shake_128"}),
            ((), {"algorithm": 5}),
            ((), {"chunk_size": 0}),
            ((), {"chunk_size": -1}),
            ((), {"chunk_size": True}),
            ((), {"chunk_size": "x"}),
        ],
        verbose=False,
    )


@pytest.mark.parametrize(
    "algorithm",
    [
        "md5", "sha1", "sha224", "sha256", "sha384", "sha512",
        "sha3_224", "sha3_256", "sha3_384", "sha3_512", "blake2b", "blake2s",
    ],
)
def test_file_hash_uses_the_requested_algorithm(tmp_path, algorithm) -> None:
    target = tmp_path / "a.bin"
    target.write_bytes(b"hello world")
    assert FileHash(algorithm=algorithm)(target) == hashlib.new(algorithm, b"hello world").hexdigest()


@pytest.mark.parametrize("chunk_size", [1, 2, 5, 100, 1_000_000])
def test_file_hash_does_not_depend_on_the_chunk_size(tmp_path, chunk_size) -> None:
    data = bytes(range(256)) * 4
    target = tmp_path / "a.bin"
    target.write_bytes(data)
    assert FileHash(chunk_size=chunk_size)(target) == hashlib.sha256(data).hexdigest()


def test_file_hash_depends_on_content_only(tmp_path) -> None:
    (tmp_path / "x").mkdir()
    (tmp_path / "y").mkdir()
    one, two, other = tmp_path / "x" / "a.txt", tmp_path / "y" / "b.dat", tmp_path / "c.txt"
    one.write_bytes(b"same")
    two.write_bytes(b"same")
    other.write_bytes(b"sbme")
    action = FileHash()
    assert action(one) == action(two)
    assert action(one) != action(other)


def test_file_hash_is_a_lowercase_hex_digest(tmp_path) -> None:
    target = tmp_path / "a.bin"
    target.write_bytes(b"abc")
    digest = FileHash()(target)
    assert digest == digest.lower()
    assert len(digest) == 64
    int(digest, 16)


def test_file_hash_runs_asynchronously(tmp_path) -> None:
    target = tmp_path / "a.bin"
    target.write_bytes(b"abc")
    assert asyncio.run(FileHash().acall(target)) == hashlib.sha256(b"abc").hexdigest()
