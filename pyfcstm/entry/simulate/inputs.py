"""Explicit command-supplied input vectors for the simulator CLI."""

from typing import List

from ...simulate import BaseIntegratedInputPattern


class _CommandInput(BaseIntegratedInputPattern):
    """Bind names at construction; supply a complete vector before each call."""

    def __init__(self, input_names):
        super().__init__(input_names)
        self.values = {}

    def _sample(self, step):
        return self.values


def _assignments(items, parse_value):
    """Parse explicit numeric assignments, rejecting duplicates and omissions."""
    values = {}
    for item in items:
        if "=" not in item:
            raise ValueError("Expected name=value, got %r" % item)
        name, value = item.split("=", 1)
        if not name or name in values:
            raise ValueError("Empty or duplicate assignment name: %r" % name)
        values[name] = parse_value(value)
    return values


def split_init_arguments(text: str) -> List[str]:
    """
    Split the text after ``init`` into the start position and the assignments.

    The start position is the first word, except that a configuration text such
    as ``Controller.Running{Safety: Watching, Motion: On}`` holds spaces inside
    its braces and stays one argument; spaces before the opening brace belong to
    it as well, as the configuration parser allows them. The words after it are the variable
    assignments. Unbalanced braces are left to the configuration parser to
    report: the whole text then becomes the start position.

    :param text: The command line after the word ``init``.
    :type text: str
    :return: The start position followed by the assignments; empty when the text
        is blank.
    :rtype: List[str]

    Example::

        >>> from pyfcstm.entry.simulate.inputs import split_init_arguments
        >>> split_init_arguments(' System.Active counter=10')
        ['System.Active', 'counter=10']
        >>> split_init_arguments('Root.P{A: X, B: [done]} n=1 m=2')
        ['Root.P{A: X, B: [done]}', 'n=1', 'm=2']
        >>> split_init_arguments('Root.P {A: X} n=1')
        ['Root.P {A: X}', 'n=1']
        >>> split_init_arguments('Root.P{A: X')
        ['Root.P{A: X']
    """
    text = text.strip()
    if not text:
        return []
    depth = 0
    end = len(text)
    for index, char in enumerate(text):
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                end = index + 1
                break
        elif char.isspace() and depth == 0 and not text[index:].lstrip().startswith('{'):
            end = index
            break
    return [text[:end]] + text[end:].split()
