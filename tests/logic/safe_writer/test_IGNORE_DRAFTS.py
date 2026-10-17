import fnmatch
import pytest
from simplibs.file.logic.safe_writer import IGNORE_DRAFTS


def _is_draft_name(name: str) -> bool:
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in IGNORE_DRAFTS)


def test_ignore_drafts_is_an_immutable_set_of_patterns() -> None:
    """A frozenset of glob patterns, safe to union with DEFAULT_IGNORE_NAMES."""
    assert isinstance(IGNORE_DRAFTS, frozenset)
    assert IGNORE_DRAFTS
    assert all(isinstance(pattern, str) for pattern in IGNORE_DRAFTS)


@pytest.mark.parametrize(
    "name",
    [
        ".x.abcdefgh.draft",
        ".report.txt.a1b2c3d4.draft",
        ".data.tar.gz.00ff00ff.draft",
        ".a.b.abcdefgh.draft",
    ],
)
def test_ignore_drafts_matches_draft_names(name) -> None:
    """A hidden name with exactly an 8-character middle part looks like a draft."""
    assert _is_draft_name(name)


@pytest.mark.parametrize(
    "name",
    [
        "essay.draft",
        ".notes.draft",
        ".a.b.draft",
        "report.txt",
        "x.abcdefgh.draft",
        ".x.abcdefg.draft",
        ".x.abcdefghi.draft",
        ".x.abcdefgh.drafts",
    ],
)
def test_ignore_drafts_does_not_hide_ordinary_files(name) -> None:
    """The pattern is narrow on purpose: a user's own `essay.draft` must stay visible."""
    assert not _is_draft_name(name)
