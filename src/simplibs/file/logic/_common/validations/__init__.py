from .raise_destination_exists_error import raise_destination_exists_error
from .raise_destination_is_dir_error import raise_destination_is_dir_error
from .raise_file_access_error import raise_file_access_error
from .raise_file_not_found_error import raise_file_not_found_error
from .raise_not_a_file_error import raise_not_a_file_error


_DESIGN_NOTES = """
# File Common Diagnostic Helpers Sub-Package

## Purpose
Internal diagnostic helpers raising structured exceptions for file operations
across the library.

## Internal Components Registry

| Component                       | Type     | Description                                                           |
| :------------------------------ | :------- | :-------------------------------------------------------------------- |
| `raise_destination_exists_error`| Function | Raises `AlreadyExistsError` when a destination already exists.        |
| `raise_destination_is_dir_error`| Function | Raises `StateError` when a destination path is an existing directory. |
| `raise_file_access_error`       | Function | Raises `AccessError` when the OS refuses an operation on a file.      |
| `raise_file_not_found_error`    | Function | Raises `NotFoundError` when a required file is missing.               |
| `raise_not_a_file_error`        | Function | Raises `StateError` when a path is not a regular file.                |
"""