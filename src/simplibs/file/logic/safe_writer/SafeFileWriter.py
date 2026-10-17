from pathlib import Path
from types import TracebackType
from typing import IO, Any
from simplibs.path import PathLike, ensure_parent_dir, normalize_path
from simplibs.validate import validate_call
# Outers
from ...annotations import EncodingErrors, EncodingName, NewlineMode, WriterMode
from .._common.validations import (
    raise_destination_is_dir_error,
    raise_file_access_error,
)
from .._common.helpers import commit_draft, create_draft, delete_draft
# Inners
from ._validations import (
    raise_safe_writer_commit_error,
    raise_safe_writer_draft_create_error,
    raise_safe_writer_draft_open_error,
)


class SafeFileWriter:
    """Context manager for crash-safe file writing via a draft-and-swap strategy.

    Writes go into a private draft next to the target; the draft replaces the
    target in one atomic step, only when the `with` block ends without an
    exception. Any exception inside the block — or a failure of the swap itself —
    leaves the original file exactly as it was and removes the draft.

    Supports overwrite (`"w"`/`"wb"`) and append (`"a"`/`"ab"`). Append copies
    the existing content into the draft first, so its cost grows with the file.

    Example:
        with SafeFileWriter(path, mode="w") as handle:
            handle.write(content)
    """

    __slots__ = (
        "_target_path",
        "_mode",
        "_encoding",
        "_errors",
        "_newline",
        "_sync",
        "_draft_path",
        "_handle",
    )

    # ----------------------------------------------------------------------
    # Constructor initialization
    # ----------------------------------------------------------------------
    @validate_call
    def __init__(
        self,
        target_path: PathLike,
        *,
        mode: WriterMode = "w",
        encoding: EncodingName = "utf-8",
        errors: EncodingErrors = "strict",
        newline: NewlineMode = "\n",
        sync: bool = False,
    ) -> None:
        """Prepare a writer for a target path and mode. Nothing touches the disk yet.

        Args:
            target_path: The file this writer will ultimately produce.
            mode: `"w"`/`"wb"` to overwrite, `"a"`/`"ab"` to append.
            encoding: Text encoding of the handle. Ignored in binary modes.
            errors: Handling of unencodable characters. Ignored in binary modes.
            newline: Line ending written for every `"\\n"` (`None` for the
                platform's own). Ignored in binary modes.
            sync: If True, force the finished file to stable storage before
                the swap completes (slower, survives a power loss).
        """

        # 1. Store the settings; the path is normalized once, here
        self._target_path = normalize_path(target_path)
        self._mode = mode
        self._encoding = encoding
        self._errors = errors
        self._newline = newline
        self._sync = sync

        # 2. No draft and no handle yet
        self._draft_path: Path | None = None
        self._handle: IO[Any] | None = None

    # ----------------------------------------------------------------------
    # Context manager definition
    # ----------------------------------------------------------------------
    def __enter__(self) -> IO[Any]:
        """Create the draft and open it for writing."""

        # 1. Guarantee the target's folder
        ensure_parent_dir(self._target_path)

        # 2. A directory at the target can never be replaced by a file
        if self._target_path.is_dir():
            raise_destination_is_dir_error(self._target_path, self._operation)

        # 3. Create the draft — pre-filled with the existing content for append modes
        try:
            self._draft_path = create_draft(self._target_path, append=self._is_append)
        except OSError as caught_exc:
            raise_safe_writer_draft_create_error(self._target_path, caught_exc)

        # 4. Open it; a failure removes the draft that was just created
        try:
            self._handle = self._open_draft()
        except OSError as caught_exc:
            delete_draft(self._draft_path)
            self._draft_path = None
            raise_safe_writer_draft_open_error(self._target_path, caught_exc)

        # 5. Hand the open handle to the caller
        return self._handle

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        """Commit the draft on success, discard it on any failure."""

        # 1. Take the state and reset it — a writer instance is single-use
        handle, draft_path = self._handle, self._draft_path
        self._handle, self._draft_path = None, None

        # 2. Close the handle first; remember a failure (a full disk shows up here) instead of raising it
        close_error: OSError | None = None
        if handle is not None:
            try:
                handle.close()
            except OSError as caught_exc:
                close_error = caught_exc

        # 3. An exception from the block wins — discard the draft, keep the original, let it propagate untouched
        if exc_type is not None:
            delete_draft(draft_path)
            return False

        # 4. The data never fully reached the draft — discard it and say so
        if close_error is not None:
            delete_draft(draft_path)
            raise_file_access_error(self._target_path, self._operation, close_error)

        # 5. Success — swap the draft in; a failed swap leaves the original untouched
        try:
            commit_draft(draft_path, self._target_path, sync=self._sync)
        except OSError as caught_exc:
            delete_draft(draft_path)
            raise_safe_writer_commit_error(self._target_path, caught_exc)

        # 6. Never suppress an exception
        return False

    # ----------------------------------------------------------------------
    # Internals
    # ----------------------------------------------------------------------
    @property
    def _is_append(self) -> bool:
        return "a" in self._mode

    @property
    def _operation(self) -> str:
        return "append" if self._is_append else "write"

    def _open_draft(self) -> IO[Any]:
        """Open the draft in the mode the caller asked for."""

        # 1. Append drafts already hold the old content, so "a" continues after it
        open_mode = "a" if self._is_append else "w"

        # 2. Binary — no encoding, no newline handling
        if "b" in self._mode:
            return self._draft_path.open(open_mode + "b")

        # 3. Text — encoding, error handler and line ending as requested
        return self._draft_path.open(
            open_mode,
            encoding=self._encoding,
            errors=self._errors,
            newline=self._newline,
        )


_DESIGN_NOTES = """
# SafeFileWriter — Draft-and-Swap Writing

## Purpose
The one place in the library that knows how to replace a file safely. Every
writer (`write_bytes`, `append_bytes`, and through them all the text and JSON
writers) goes through it unless the caller opts out with `use_draft=False`.

---

## 1. What It Guarantees
* The target is replaced in one `os.replace` — a reader sees the old file or
  the new one, never half of each.
* An exception inside the `with` block, a failed close and a failed swap all
  leave the original untouched and remove the draft.
* Safe against a crashing PROCESS. Against a power loss only with
  `sync=True` (see `commit_draft`).

## 2. What Changed From the Old Writer
* **Unique draft** (`create_draft`) instead of `name.draft` — two writers no
  longer interleave, a crash leftover is never reused.
* **No leak when opening fails** — the draft is deleted before the card is raised.
* **No masked error** — the old `__exit__` closed the handle first; if the
  close failed (full disk) the exception flew out before the draft was deleted
  and hid the real error. Now a close failure is remembered and only reported
  when the block itself succeeded.
* **`mode` is a `WriterMode`** — `"x"` / `"r+"` are rejected up front.
* **Permissions are kept** on replacement (`commit_draft`).
* **`sync`**, **`errors`**, **`newline`** parameters.
* A **directory at the target** is a clear `StateError` instead of an obscure
  `PermissionError` from the swap.

## 3. Single-Use
`__exit__` resets the state; entering a used instance again simply creates a
new draft. The instance is meant for one `with` statement.

## 4. Text Mode and BOM
In text append mode Python's own `TextIOWrapper` knows the draft already has
content and does not write a second BOM for `utf-8-sig`/`utf-16`.

## 5. Symlinks
The path is normalized (symlinks resolved), so writing through a link
replaces the file the link points to and leaves the link in place.

## TODO(test)
* Exception in the block -> original intact, no `.draft` left.
* `handle.close()` raising -> `AccessError`, original intact, draft removed.
* `commit_draft` raising -> `AccessError`, original intact, draft removed.
* Open of the draft failing -> draft removed.
* Two writers of one target at once -> two distinct drafts, last commit wins, no interleaving.
* Mode of an existing file preserved; new file honours the umask.
* Append twice with `utf-8-sig` -> one BOM only.
* Target is a directory -> `StateError`.
* Entering an instance twice.
"""
