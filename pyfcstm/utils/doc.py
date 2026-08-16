"""Normalization and validation helpers for FCSTM documentation blocks.

The helpers deliberately keep documentation opaque while making its transport
through the AST and model deterministic::

    >>> format_multiline_comment('/*\\n * Ready state\\n */')
    'Ready state'
    >>> format_multiline_comment('/*\\r\\n * Ready\\r\\n */')
    'Ready'
    >>> validate_documentation_for_export('Ready')
    >>> aggregate_documentation((None, 'Ready', 'Ready', 'Running'))
    'Ready\\n\\nRunning'
"""

import textwrap
from typing import Iterable, Optional


def format_multiline_comment(raw_doc: str) -> str:
    """Return the canonical opaque body of a ``/* ... */`` block.

    The parser deliberately keeps documentation opaque.  This helper only
    removes comment framing and one decorative star margin; it does not parse
    Markdown or otherwise rewrite the body.

    >>> format_multiline_comment('/* text */')
    'text'
    >>> format_multiline_comment('/*\\n * A\\n * B\\n */')
    'A\\nB'
    """
    if not isinstance(raw_doc, str):
        raise TypeError("documentation comment must be a str")

    source = raw_doc.strip().replace("\r\n", "\n").replace("\r", "\n")
    if not source.startswith("/*"):
        raise ValueError("documentation comment is not a complete block: missing '/*'")
    close = source.find("*/", 2)
    if close < 0 or close != len(source) - 2:
        raise ValueError("documentation comment must have one complete terminator")

    body = source[2:close]
    # Javadoc/Doxygen opener decoration is recoverable, but only one marker.
    if body.startswith("*") and source.startswith("/**"):
        body = body[1:]
    elif body.startswith("!") and source.startswith("/*!"):
        body = body[1:]

    has_lf = "\n" in body
    lines = body.split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    nonblank = [line for line in lines if line.strip()]
    margin = False
    inline_first = False
    if has_lf and nonblank:
        margin = all(line.lstrip(" \t").startswith("*") for line in nonblank)
        # A first body line sharing the opener may omit the decorative star.
        if not margin and source.startswith("/*") and "\n" in body:
            original_lines = body.split("\n")
            first_is_inline = bool(original_lines and original_lines[0].strip())
            rest = [line for line in original_lines[1:] if line.strip()]
            margin = first_is_inline and bool(rest) and all(
                line.lstrip(" \t").startswith("*") for line in rest
            )
            inline_first = margin and first_is_inline

    if margin:
        stripped = []
        for index, line in enumerate(lines):
            if not line.strip():
                stripped.append("")
                continue
            content = line.lstrip(" \t")
            if not (inline_first and index == 0):
                content = content[1:]
                if content.startswith((" ", "\t")):
                    content = content[1:]
            stripped.append(content)
        lines = stripped

    lines = [line if line.strip() else "" for line in lines]
    body = textwrap.dedent("\n".join(lines))
    body_lines = body.split("\n") if body else []
    if body_lines:
        first = next((i for i, line in enumerate(body_lines) if line.strip()), None)
        last = next((i for i in range(len(body_lines) - 1, -1, -1) if body_lines[i].strip()), None)
        if first is not None:
            body_lines[first] = body_lines[first].lstrip(" \t")
            body_lines[last] = body_lines[last].rstrip(" \t")
            body_lines = body_lines[first : last + 1]
            body = "\n".join(body_lines)

    if "/*" in body:
        raise ValueError("documentation body contains '/*'; a prior comment may be unterminated")
    if "*/" in body:
        raise ValueError("documentation body contains '*/'")
    validate_documentation_for_export(body)
    return body


def validate_documentation_for_export(doc: str) -> None:
    """Validate a normalized documentation value before canonical export.

    >>> validate_documentation_for_export('A\\nB')
    >>> validate_documentation_for_export('A /* B')
    Traceback (most recent call last):
        ...
    ValueError: documentation must not contain '/*'
    """
    if not isinstance(doc, str):
        raise TypeError("documentation must be a str")
    if "\r" in doc:
        raise ValueError("documentation must not contain CR")
    if "/*" in doc:
        raise ValueError("documentation must not contain '/*'")
    if "*/" in doc:
        raise ValueError("documentation must not contain '*/'")
    invalid_control = next(
        (
            char
            for char in doc
            if (ord(char) < 0x20 and char not in "\n\t") or ord(char) == 0x7F
        ),
        None,
    )
    if invalid_control is not None:
        raise ValueError(
            "documentation contains unsupported control character "
            f"U+{ord(invalid_control):04X}"
        )
    if doc and (doc[0].isspace() or doc[-1].isspace()):
        raise ValueError("documentation has invalid boundary whitespace")
    if any(line and line.isspace() for line in doc.split("\n")):
        raise ValueError("documentation contains whitespace-only line")


def aggregate_documentation(docs: Iterable[Optional[str]]) -> Optional[str]:
    """Stable, ordered aggregation of normalized documentation values.

    >>> aggregate_documentation((None, '', 'A', 'A', 'B'))
    'A\\n\\nB'
    >>> aggregate_documentation((None, None)) is None
    True
    """
    values = list(docs)
    if not values or all(value is None for value in values):
        return None
    seen = set()
    nonempty = []
    saw_empty = False
    for value in values:
        if value is None:
            continue
        validate_documentation_for_export(value)
        if value == "":
            saw_empty = True
        elif value not in seen:
            seen.add(value)
            nonempty.append(value)
    result = "\n\n".join(nonempty) if nonempty else ("" if saw_empty else None)
    if result is not None:
        validate_documentation_for_export(result)
    return result
