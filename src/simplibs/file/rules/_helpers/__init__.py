from .FilePartIs import FilePartIs
from .read_file_head import read_file_head
from .read_file_size import read_file_size


_DESIGN_NOTES = """
# rules/_helpers — Shared Internals of the File Rules

Plain imports, not exported from the package.

## Internal Components Registry

| Component        | Type     | Description                                                          |
| :--------------- | :------- | :------------------------------------------------------------------- |
| `FilePartIs`     | Class    | Abstract base for rules judging a measurable part of a file.         |
| `read_file_head` | Function | Reads and decodes the beginning of a file without raising.           |
| `read_file_size` | Function | Reads the size of a regular file without raising.                    |
"""