def strip_line_ending(line: str) -> str:
    """Remove exactly one trailing line ending (`\\r\\n`, `\\n` or `\\r`) from a line.

    Args:
        line: A line as produced by an untranslated (`newline=""`) read.

    Returns:
        The line without its terminator; a line without one is returned unchanged.
    """

    # 1. The two-character ending first, or "\r\n" would lose only its "\n"
    if line.endswith("\r\n"):
        return line[:-2]

    # 2. A single-character ending
    if line.endswith(("\n", "\r")):
        return line[:-1]

    # 3. The last line of a file may have none
    return line


_DESIGN_NOTES = """
# strip_line_ending — One Terminator, Not `rstrip`

`str.rstrip("\\r\\n")` would also eat characters that belong to the line
(`"a\\r"` followed by an empty line is two lines in an untranslated read).
Exactly one ending is removed, the longest first.
"""
