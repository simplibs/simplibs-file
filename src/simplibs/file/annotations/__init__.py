from .ByteCount import ByteCount
from .EncodingErrors import EncodingErrors
from .EncodingName import EncodingName
from .HashAlgorithm import HashAlgorithm
from .NewlineMode import NewlineMode
from .WriterMode import WriterMode


_DESIGN_NOTES = """
# annotations — Shared Types of simplibs-file

Plain imports, no `__all__` (the package root decides what is public).
`PathLike` is not redefined here — it comes from `simplibs.path`.

## Internal Components Registry

| Component      | Type             | Description                                                     |
| :------------- | :--------------- | :-------------------------------------------------------------- |
| `ByteCount`    | Validated Type   | A validated positive integer representing a number of bytes.    |
| `EncodingErrors`| Literal Type    | Allowed encoding error handling strategies for read/write.      |
| `EncodingName` | Validated Type   | A validated string representing a valid Python text encoding.   |
| `HashAlgorithm`| Literal Type     | Guaranteed fixed-length hash algorithms from `hashlib`.         |
| `NewlineMode`  | Literal / None   | Deterministic line ending modes for text writing.               |
| `WriterMode`   | Literal Type     | Supported open modes for `SafeFileWriter` (`w`, `wb`, `a`, `ab`).|
"""