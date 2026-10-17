from .AppendBytesTo import AppendBytesTo
from .AppendTextTo import AppendTextTo
from .WriteAggregatedTo import WriteAggregatedTo
from .WriteBytesTo import WriteBytesTo
from .WriteJsonTo import WriteJsonTo
from .WriteLinesTo import WriteLinesTo
from .WriteTextTo import WriteTextTo


_DESIGN_NOTES = """
# File Actions Destinations Sub-Package

## Purpose
Pipeline actions wrapping file writing functions where the **path** is the main
pipeline input (flowing in) and the content (text, bytes, lines, fragments) is
configured as a parameter (e.g. `ForEach(WriteTextTo(text="placeholder"))`).

This serves as the destination-focused counterpart to the content-focused `write`
sub-package.

## Internal Components Registry

| Component           | Type   | Description                                                     |
| :------------------ | :----- | :-------------------------------------------------------------- |
| `AppendBytesTo`     | Action | Appends configured bytes to the incoming path.                  |
| `AppendTextTo`      | Action | Appends configured text to the incoming path.                   |
| `WriteAggregatedTo` | Action | Writes configured joined text fragments to the incoming path.   |
| `WriteBytesTo`      | Action | Writes configured bytes to the incoming path.                   |
| `WriteJsonTo`       | Action | Writes configured JSON data to the incoming path.               |
| `WriteLinesTo`      | Action | Writes configured lines to the incoming path.                   |
| `WriteTextTo`       | Action | Writes configured text to the incoming path.                    |
"""