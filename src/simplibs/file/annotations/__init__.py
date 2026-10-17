from .ByteCount import ByteCount
from .EncodingErrors import EncodingErrors
from .EncodingName import EncodingName
from .HashAlgorithm import HashAlgorithm
from .NewlineMode import NewlineMode
from .TextCollection import TextCollection
from .WriterMode import WriterMode


_DESIGN_NOTES = """
# annotations — Shared Types of simplibs-file

Plain imports, no `__all__` (the package root decides what is public).
`PathLike` is not redefined here — it comes from `simplibs.path`.

## Internal Components Registry

| Component       | Type             | Description                                                       |
| :-------------- | :--------------- | :---------------------------------------------------------------- |
| `ByteCount`     | Annotated Type   | A positive integer representing a number of bytes.                |
| `EncodingErrors`| Literal Type     | Allowed encoding error handling strategies for read/write.        |
| `EncodingName`  | Annotated Type   | A string naming a Python text encoding that works both ways.      |
| `HashAlgorithm` | Literal Type     | Guaranteed fixed-length hash algorithms from `hashlib`.           |
| `NewlineMode`   | Literal / None   | Deterministic line ending modes for text writing.                 |
| `TextCollection`| Annotated Type   | A collection of texts (lines, fragments) — never a bare string.   |
| `WriterMode`    | Literal Type     | Supported open modes for `SafeFileWriter` (`w`, `wb`, `a`, `ab`). |
"""