"""Deliberately break the library, one change at a time, and check that the tests notice.

For every mutation below the script
  1. makes sure the original text is in the file exactly once,
  2. writes the broken version,
  3. runs the test suite (it stops at the first failing test),
  4. puts the original file back — always, even after Ctrl+C or a crash.

KILLED   = at least one test failed: the tests guard this behaviour.
SURVIVED = every test passed although the code is wrong: there is a gap in the tests.

Usage (from the repository root, with the dev dependencies installed):

    python tools/mutation_check.py              # run all mutations
    python tools/mutation_check.py --check      # only verify that every anchor text is found (no tests run)
    python tools/mutation_check.py --only 3 7   # run just these numbers
    python tools/mutation_check.py --command "python -m pytest -x -q tests/logic"   # a different test command
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "simplibs" / "file"
BACKUP_SUFFIX = ".mutation_orig"
DEFAULT_COMMAND = f"{sys.executable} -m pytest -x -q -p no:cacheprovider -p no:cov --no-header tests"


@dataclass(frozen=True)
class Mutation:
    number: int
    title: str
    file: str            # relative to src/simplibs/file
    old: str
    new: str
    note: str = ""       # shown when the mutation survives
    only_on: str | None = None    # "nt" or "posix": the tests that catch it exist only there


MUTATIONS: list[Mutation] = [
    Mutation(
        1, "commit_draft: do not keep the permissions of the replaced file",
        "logic/_common/helpers/commit_draft.py",
        "if keep_mode and target_path.is_file():",
        "if False and target_path.is_file():",
        note="POSIX mode tests and the Windows read-only-flag tests both guard this; check that neither was skipped.",
    ),
    Mutation(
        2, "write_bytes: write straight into the target instead of through a draft",
        "logic/write/write_bytes.py",
        "    if use_draft:\n        try:\n            with SafeFileWriter(",
        "    if False:\n        try:\n            with SafeFileWriter(",
    ),
    Mutation(
        3, "delete_file: delete the target of a symlink instead of the link",
        "logic/operations/delete_file.py",
        "        entry.unlink()\n\n    # 5.1 It vanished since the check",
        "        entry.resolve().unlink()\n\n    # 5.1 It vanished since the check",
        note="Needs symlinks: turn on Developer Mode on Windows, otherwise those tests are skipped.",
    ),
    Mutation(
        4, "drop_redundant_bom: never remove the BOM when appending",
        "logic/write/_helpers/drop_redundant_bom.py",
        "return data[len(preamble):] if has_content else data",
        "return data",
    ),
    Mutation(
        5, "is_text_file: stop looking for the NUL character",
        "logic/inspection/is_text_file.py",
        'return "\\x00" not in text',
        "return True",
    ),
    Mutation(
        6, "file_hash: lose one byte at every chunk boundary",
        "logic/inspection/file_hash.py",
        "digest.update(chunk)",
        "digest.update(chunk[:chunk_size - 1])",
    ),
    Mutation(
        7, "prepare_destination: compare paths as Path objects again (the old `destination == source`)",
        "logic/operations/_helpers/prepare_destination.py",
        "if str(destination) == str(source):",
        "if destination == source:",
        note="Only Windows treats `a.txt` and `A.txt` as equal Paths, so only the Windows case-only rename tests catch it.",
        only_on="nt",
    ),
]


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _restore_leftovers() -> None:
    """A crashed earlier run may have left a broken file behind — put every original back first."""
    for backup in SRC.rglob(f"*{BACKUP_SUFFIX}"):
        original = backup.with_name(backup.name[: -len(BACKUP_SUFFIX)])
        original.write_bytes(backup.read_bytes())
        backup.unlink()
        print(f"restored {original.relative_to(ROOT)} from an interrupted run")


def _locate(mutation: Mutation) -> tuple[Path, str]:
    path = SRC / mutation.file
    if not path.is_file():
        raise SystemExit(f"[{mutation.number}] file not found: {path}")
    text = path.read_bytes().decode("utf-8")
    crlf = "\r\n" in text
    normalized = text.replace("\r\n", "\n")
    count = normalized.count(mutation.old)
    if count != 1:
        raise SystemExit(
            f"[{mutation.number}] the text to break was found {count}x in {mutation.file} (expected once) — "
            "the source changed; update the mutation."
        )
    return path, ("crlf" if crlf else "lf")


def _mutated_text(path: Path, mutation: Mutation) -> bytes:
    text = path.read_bytes().decode("utf-8")
    crlf = "\r\n" in text
    normalized = text.replace("\r\n", "\n").replace(mutation.old, mutation.new)
    compile(normalized, str(path), "exec")        # a mutation must stay valid Python
    return (normalized.replace("\n", "\r\n") if crlf else normalized).encode("utf-8")


def run_mutation(mutation: Mutation, command: list[str]) -> str:
    path, _ = _locate(mutation)
    original_bytes = path.read_bytes()
    original_digest = _digest(path)
    backup = path.with_name(path.name + BACKUP_SUFFIX)
    backup.write_bytes(original_bytes)
    try:
        path.write_bytes(_mutated_text(path, mutation))
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
    finally:
        path.write_bytes(original_bytes)
        backup.unlink(missing_ok=True)
    if _digest(path) != original_digest:
        raise SystemExit(f"!!! {path} was not restored correctly — restore it from version control")

    if result.returncode == 0:
        return "SURVIVED"
    if result.returncode == 1:
        return "KILLED"
    tail = "\n".join((result.stdout + result.stderr).strip().splitlines()[-8:])
    print(f"    pytest exited with code {result.returncode} (not a normal test failure):\n{tail}")
    return "ERROR"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="only verify that every anchor text is found")
    parser.add_argument("--only", type=int, nargs="+", metavar="N", help="run only these mutation numbers")
    parser.add_argument("--command", default=DEFAULT_COMMAND, help="the test command to run for each mutation")
    args = parser.parse_args()

    _restore_leftovers()
    chosen = [m for m in MUTATIONS if not args.only or m.number in args.only]
    command = shlex.split(args.command, posix=(os.name != "nt"))

    if args.check:
        for mutation in chosen:
            path, newline = _locate(mutation)
            _mutated_text(path, mutation)
            print(f"[{mutation.number}] ok  ({newline})  {mutation.title}")
        print("all anchors found; every mutated file is valid Python")
        return 0

    results: list[tuple[Mutation, str]] = []
    for mutation in chosen:
        print(f"[{mutation.number}] {mutation.title} ...", flush=True)
        results.append((mutation, run_mutation(mutation, command)))
        print(f"    -> {results[-1][1]}", flush=True)

    print("\n" + "=" * 78)
    gaps = 0
    for mutation, outcome in results:
        print(f"{outcome:9} [{mutation.number}] {mutation.title}")
        if outcome != "KILLED":
            expected = mutation.only_on is not None and os.name != mutation.only_on
            if expected:
                print(f"          expected on this system: {mutation.note}")
            else:
                gaps += 1
                if mutation.note:
                    print(f"          hint: {mutation.note}")
    print("=" * 78)
    print("no gaps found" if gaps == 0 else f"{gaps} gap(s) — a test is missing or was skipped")
    return 0 if gaps == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
