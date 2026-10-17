from .AppendBytes import AppendBytes
from .AppendText import AppendText
from .WriteAggregated import WriteAggregated
from .WriteBytes import WriteBytes
from .WriteJson import WriteJson
from .WriteLines import WriteLines
from .WriteText import WriteText


_DESIGN_NOTES = """
# File Actions Write Sub-Package

## Purpose
Pipeline actions wrapping file writing functions (`write_bytes`, `write_text`,
`write_lines`, `write_aggregated`, `write_json`, and appenders). These actions
take content as the main pipeline input and write it to a configured path.

## Internal Components Registry

| Component         | Type   | Description                                                     |
| :---------------- | :----- | :-------------------------------------------------------------- |
| `AppendBytes`     | Action | Appends incoming bytes to the configured path.                  |
| `AppendText`      | Action | Appends incoming text to the configured path.                   |
| `WriteAggregated` | Action | Joins incoming text fragments and writes them to the path.      |
| `WriteBytes`      | Action | Writes incoming bytes to the configured path.                   |
| `WriteJson`       | Action | Serializes incoming data to JSON and writes it to the path.     |
| `WriteLines`      | Action | Writes incoming lines to the configured path, one per line.     |
| `WriteText`       | Action | Writes incoming text to the configured path.                    |
"""