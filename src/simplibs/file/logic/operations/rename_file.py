# Inners
from .move_file import move_file


rename_file = move_file
"""Alias of `move_file` — the name this operation had before it learned to cross devices."""


_DESIGN_NOTES = """
# rename_file — the Old Name, Kept

## Purpose
Code written against `rename_file` keeps working. It is the very same function
object as `move_file` (same parameters, same behaviour), so there is nothing to
keep in sync.

## Why an Alias, Not a Wrapper
A wrapper would be a second `@validate_call`-decorated function to document and
test. The alias cannot drift.

## Introspection Note
`rename_file.__name__` is `"move_file"`; error cards and tracebacks name the real function.
"""
