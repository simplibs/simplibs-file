from .append_bytes import append_bytes
from .append_text import append_text
from .write_aggregated import write_aggregated
from .write_bytes import write_bytes
from .write_json import write_json
from .write_lines import write_lines
from .write_text import write_text


_DESIGN_NOTES = """
# write — Everything That Writes Content

## Structure
* **Cores:** `write_bytes`, `append_bytes` — the only functions that reach the disk.
* **Text layer:** `write_text`, `append_text` — encode in memory, call the cores.
* **Shapes of text:** `write_lines`, `write_aggregated`, `write_json` — build the
  text, call `write_text`.

Plain imports, no `__all__` — the package root decides what is public.

## Internal Components Registry

| Component         | Type     | Description                                                     |
| :---------------- | :------- | :-------------------------------------------------------------- |
| `append_bytes`    | Function | Appends raw bytes to a file (second core writer).               |
| `append_text`     | Function | Appends text to a file with encoding and BOM handling.          |
| `write_aggregated`| Function | Joins text fragments with a separator and writes them as one.   |
| `write_bytes`     | Function | Writes raw bytes to a file (first core writer).                 |
| `write_json`      | Function | Serializes a value to JSON and writes it to a file.             |
| `write_lines`     | Function | Writes a collection of lines to a file, one per line.           |
| `write_text`      | Function | Encodes text in memory and writes it to a file.                 |
"""