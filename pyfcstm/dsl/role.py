"""Variable declaration roles shared by the syntax and model layers.

:class:`VariableRole` describes ownership independently of declaration spelling.
The public model API re-exports it as ``pyfcstm.model.VariableRole``.
"""

from enum import Enum


class VariableRole(str, Enum):
    """Ownership and lifetime of a declared model variable.

    Control and output values persist between cycles. Dynamic inputs belong to
    the environment; static inputs belong to the run configuration. Both input
    roles are read-only within model actions and transition effects.

    Example::

        >>> VariableRole("input_dynamic") is VariableRole.INPUT_DYNAMIC
        True
    """

    CONTROL = "control"
    INPUT_DYNAMIC = "input_dynamic"
    INPUT_STATIC = "input_static"
    OUTPUT = "output"


_DECLARATION_ROLES = {
    "def": VariableRole.CONTROL,
    "control": VariableRole.CONTROL,
    "input": VariableRole.INPUT_DYNAMIC,
    "input dynamic": VariableRole.INPUT_DYNAMIC,
    "param": VariableRole.INPUT_STATIC,
    "input static": VariableRole.INPUT_STATIC,
    "output": VariableRole.OUTPUT,
}
_DEFAULT_DECLARATIONS = {
    VariableRole.CONTROL: "def",
    VariableRole.INPUT_DYNAMIC: "input",
    VariableRole.INPUT_STATIC: "param",
    VariableRole.OUTPUT: "output",
}
