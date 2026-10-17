from simplibs.actions import create_action
# Outers
from ...logic.write import write_aggregated


WriteAggregatedTo = create_action(
    write_aggregated,
    main_param="path",
    class_name="WriteAggregatedTo",
)
"""Action wrapping `write_aggregated` — writes the configured `parts`, joined, to the path flowing in."""


_DESIGN_NOTES = """
# WriteAggregatedTo — Action Over `write_aggregated`

## Purpose
A fixed set of fragments assembled into each target.

## Shape
Main input: `path`. Path in, the written `Path` out. Sibling of `WriteAggregated`.

## Changes the Disk
This action writes, copies, moves or deletes.
"""
