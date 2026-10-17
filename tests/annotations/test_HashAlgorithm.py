import hashlib
from typing import get_args
import pytest
from simplibs.rules import IsTyping
from simplibs.file.annotations import HashAlgorithm


@pytest.mark.parametrize("value", get_args(HashAlgorithm))
def test_hash_algorithm_accepts_listed_algorithms(value) -> None:
    """Every listed fixed-length algorithm is valid."""
    assert IsTyping(HashAlgorithm).is_valid(value)


@pytest.mark.parametrize(
    "value",
    ["shake_128", "shake_256", "crc32", "SHA256", "sha-256", "", None, 256],
)
def test_hash_algorithm_rejects_everything_else(value) -> None:
    """Variable-length digests, unknown names, wrong spelling and non-strings are rejected."""
    assert not IsTyping(HashAlgorithm).is_valid(value)


@pytest.mark.parametrize("name", get_args(HashAlgorithm))
def test_hash_algorithm_is_usable_with_hashlib(name) -> None:
    """Every listed name is guaranteed by hashlib and yields a digest without a length argument."""
    assert name in hashlib.algorithms_guaranteed
    assert hashlib.new(name, usedforsecurity=False).hexdigest()


def test_hash_algorithm_lists_no_variable_length_algorithm() -> None:
    """shake_* need an explicit digest length, which file_hash does not offer."""
    assert not {"shake_128", "shake_256"} & set(get_args(HashAlgorithm))
