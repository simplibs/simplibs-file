from .file_hash import file_hash
from .file_size import file_size
from .is_text_file import is_text_file


_DESIGN_NOTES = """
# inspection — Ask a File About Itself

`file_size`, `file_hash` (strict: an error card when there is no file) and
`is_text_file` (a predicate: `False` instead of an error). None of them changes
anything. Plain imports, no `__all__`.

## Internal Components Registry

| Component      | Type     | Description                                                    |
| :------------- | :------- | :------------------------------------------------------------- |
| `file_hash`    | Function | Computes the hash of a file's content in chunks.               |
| `file_size`    | Function | Gets the size of a file in bytes without reading content.      |
| `is_text_file` | Function | Checks whether a file looks like text based on its first bytes.|
"""