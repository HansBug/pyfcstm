import os
import re
import textwrap


def format_multiline_comment(raw_doc):
    """
    Format multiline comments parsed by ANTLR4 by removing comment markers
    and aligning indentation.

    Args:
        raw_doc: Raw comment text including /* */ markers

    Returns:
        Formatted comment text with markers removed and proper indentation
    """
    if re.fullmatch(r'\s*/\*+/\s*', raw_doc.strip()):
        return ""

    # Use regex to remove opening comment markers (/* with one or more asterisks)
    content = re.sub(r'^\s*/\*+', '', raw_doc.strip())

    # Use regex to remove closing comment markers
    content = re.sub(r'\*+/\s*$', '', content)

    # Split into lines
    lines = content.splitlines()

    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    lines = lines[i:]

    i = len(lines) - 1
    while i > 0 and not lines[i].strip():
        i -= 1
    lines = lines[:i + 1]

    # Use textwrap.dedent to align indentation
    formatted_text = textwrap.dedent(os.linesep.join(map(str.rstrip, lines)))

    return formatted_text
