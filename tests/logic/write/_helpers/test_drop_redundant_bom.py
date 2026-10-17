import sys
from pathlib import Path
import pytest
from simplibs.file.logic.write._helpers import drop_redundant_bom

_ORDER = "le" if sys.byteorder == "little" else "be"


def _file(path: Path, data: bytes) -> Path:
    path.write_bytes(data)
    return path


def test_drop_redundant_bom_strips_utf8_sig_from_an_append_to_content(tmp_path: Path) -> None:
    """The BOM belongs at the start of a file, never in the middle."""
    target = _file(tmp_path / "a.txt", b"\xef\xbb\xbfab")

    assert drop_redundant_bom("c".encode("utf-8-sig"), target, "utf-8-sig") == b"c"


def test_drop_redundant_bom_keeps_the_bom_for_a_missing_target(tmp_path: Path) -> None:
    """A new file keeps its BOM."""
    data = "c".encode("utf-8-sig")

    assert drop_redundant_bom(data, tmp_path / "new.txt", "utf-8-sig") == data


def test_drop_redundant_bom_keeps_the_bom_for_an_empty_existing_file(tmp_path: Path) -> None:
    """An empty file has no content the BOM could land in the middle of."""
    target = _file(tmp_path / "a.txt", b"")
    data = "c".encode("utf-8-sig")

    assert drop_redundant_bom(data, target, "utf-8-sig") == data


def test_drop_redundant_bom_keeps_the_bom_when_the_target_is_a_directory(tmp_path: Path) -> None:
    """Only an existing regular file counts as content."""
    data = "c".encode("utf-8-sig")

    assert drop_redundant_bom(data, tmp_path, "utf-8-sig") == data


@pytest.mark.parametrize("encoding", ["utf-16", "utf-32"])
def test_drop_redundant_bom_strips_the_native_bom_of_utf16_and_utf32(tmp_path: Path, encoding) -> None:
    """The preamble is found by encoding the empty string — no list of codec names."""
    target = _file(tmp_path / "a.txt", b"already something")
    data = "ab".encode(encoding)
    expected = "ab".encode(f"{encoding}-{_ORDER}")

    assert drop_redundant_bom(data, target, encoding) == expected


@pytest.mark.parametrize("encoding", ["utf-8", "ascii", "latin-1", "cp1250"])
def test_drop_redundant_bom_leaves_encodings_without_a_preamble_alone(tmp_path: Path, encoding) -> None:
    """Most codecs write nothing in front of a chunk."""
    target = _file(tmp_path / "a.txt", b"already something")
    data = "ab".encode(encoding)

    assert drop_redundant_bom(data, target, encoding) == data


def test_drop_redundant_bom_leaves_data_without_the_preamble_alone(tmp_path: Path) -> None:
    """Bytes that do not start with the BOM are returned as they are."""
    target = _file(tmp_path / "a.txt", b"content")

    assert drop_redundant_bom(b"plain", target, "utf-8-sig") == b"plain"


def test_drop_redundant_bom_empty_data_is_unchanged(tmp_path: Path) -> None:
    """Empty data does not start with a BOM."""
    target = _file(tmp_path / "a.txt", b"content")

    assert drop_redundant_bom(b"", target, "utf-8-sig") == b""


def test_drop_redundant_bom_strips_only_one_preamble(tmp_path: Path) -> None:
    """Only the leading BOM goes; a second BOM-like sequence in the data stays."""
    target = _file(tmp_path / "a.txt", b"content")
    data = b"\xef\xbb\xbf" + b"\xef\xbb\xbf" + b"x"

    assert drop_redundant_bom(data, target, "utf-8-sig") == b"\xef\xbb\xbfx"


def test_drop_redundant_bom_unreadable_target_keeps_the_data(tmp_path: Path, monkeypatch) -> None:
    """A stat problem is not worth failing an append over."""
    target = _file(tmp_path / "a.txt", b"content")
    data = "c".encode("utf-8-sig")

    def refusing_is_file(self):
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "is_file", refusing_is_file)

    assert drop_redundant_bom(data, target, "utf-8-sig") == data
