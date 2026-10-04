"""Explicit command-supplied input vectors for the simulator CLI."""

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
