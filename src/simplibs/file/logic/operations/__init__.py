from .backup_file import backup_file
from .copy_file import copy_file
from .delete_file import delete_file
from .move_file import move_file
from .rename_file import rename_file


_DESIGN_NOTES = """
# operations — Things You Do TO a File

`copy_file`, `move_file` (+ alias `rename_file`), `delete_file`, `backup_file`.

Copies are atomic (`copy_atomically`); `move_file` and `delete_file` work on the
directory ENTRY (`normalize_entry_path`), the others on the CONTENT
(`normalize_path`). Plain imports, no `__all__`.

## Internal Components Registry

| Component     | Type     | Description                                                     |
| :------------ | :------- | :-------------------------------------------------------------- |
| `backup_file` | Function | Creates an atomic backup copy next to a file.                   |
| `copy_file`   | Function | Copies a file atomically, preserving permissions and times.     |
| `delete_file` | Function | Deletes a file or symlink entry safely.                         |
| `move_file`   | Function | Moves or renames a file across folders and devices.             |
| `rename_file` | Function | Alias of `move_file` for backward compatibility.                |
"""