from .iter_lines import iter_lines
from .read_bytes import read_bytes
from .read_json import read_json
from .read_lines import read_lines
from .read_text import read_text


_DESIGN_NOTES = """
# read — Everything That Reads Content

## Structure
* **Core:** `read_bytes` — the only function that reads the disk eagerly.
* **Text layer:** `read_text`, `read_lines`, `read_json` — decode in memory.
* **Lazy:** `iter_lines` — streams, never holds the file.

Plain imports, no `__all__` — the package root decides what is public.

## Internal Components Registry

| Component   | Type     | Description                                                     |
| :---------- | :------- | :-------------------------------------------------------------- |
| `iter_lines`| Function | Streams lines of a file lazily without loading it whole.        |
| `read_bytes`| Function | Reads the full binary content of a file (core reader).          |
| `read_json` | Function | Reads a file and parses its content as JSON.                    |
| `read_lines`| Function | Reads a file as a list of lines with exact endings.             |
| `read_text` | Function | Reads the full text of a file with normalized newlines.         |
"""