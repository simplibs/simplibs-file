from simplibs.actions import create_action
# Outers
from ...logic.write import write_aggregated


WriteAggregated = create_action(
    write_aggregated,
    main_param="parts",
    class_name="WriteAggregated",
)
"""Action wrapping `write_aggregated` — joins the text fragments flowing in and writes them to the configured `path`."""


_DESIGN_NOTES = """
# WriteAggregated — Action Over `write_aggregated`

## Purpose
`CollectFiles(...) >> ForEach(ReadText()) >> WriteAggregated(path=combined)` — many files become one.

## Shape
Main input: `parts`. A list of texts in, the written `Path` out. This is why the CONTENT is the pipeline value for writers: the list is what a pipeline has at hand. Sibling: `WriteAggregatedTo`.

## Changes the Disk
This action writes, copies, moves or deletes.
"""
