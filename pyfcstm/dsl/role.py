"""Variable declaration roles shared by the syntax and model layers.

:class:`VariableRole` describes ownership independently of declaration spelling.
The public model API re-exports it as ``pyfcstm.model.VariableRole``.
"""

from enum import Enum


class VariableRole(str, Enum):
    """Ownership and lifetime of a declared model variable.

    Control and output values persist between cycles. Inputs belong to
    the environment; parameters belong to the run configuration. Both are
    read-only within model actions and transition effects.

    Example::

        >>> VariableRole("input") is VariableRole.INPUT
        True
    """

    CONTROL = "control"
    INPUT = "input"
    PARAM = "param"
    OUTPUT = "output"


_DECLARATION_ROLES = {
    "def": VariableRole.CONTROL,
    "control": VariableRole.CONTROL,
    "input": VariableRole.INPUT,
    "param": VariableRole.PARAM,
    "output": VariableRole.OUTPUT,
}
_DEFAULT_DECLARATIONS = {
    VariableRole.CONTROL: "def",
    VariableRole.INPUT: "input",
    VariableRole.PARAM: "param",
    VariableRole.OUTPUT: "output",
}
