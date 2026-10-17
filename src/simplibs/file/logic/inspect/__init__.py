from .file_hash import file_hash
from .file_size import file_size
from .is_text_file import is_text_file


_DESIGN_NOTES = """
# inspect — Ask a File About Itself

`file_size`, `file_hash` (strict: an error card when there is no file) and
`is_text_file` (a predicate: `False` instead of an error). None of them changes
anything. Plain imports, no `__all__`.

## Folder Name
`inspect` is also a standard-library module. Inside this package every import is
relative or fully qualified, so there is no clash — but a test runner that puts
the folder's PARENT on `sys.path` would shadow the stdlib module. If that ever
bites, rename the folder (e.g. `inspection`); nothing else refers to the name.

## Internal Components Registry

| Component      | Type     | Description                                                    |
| :------------- | :------- | :------------------------------------------------------------- |
| `file_hash`    | Function | Computes the hash of a file's content in chunks.               |
| `file_size`    | Function | Gets the size of a file in bytes without reading content.      |
| `is_text_file` | Function | Checks whether a file looks like text based on its first bytes.|
"""