"""
Simulation runtime for executing finite state machine models.

This module provides a runtime environment for simulating the execution of
hierarchical state machines defined using the pyfcstm DSL. It handles state
transitions, lifecycle actions, aspect-oriented programming, and variable
operations.

The main public components are:

* :class:`SimulationRuntime` - Runtime environment for executing state machines

.. note::
   The simulation runtime follows the exact execution semantics defined in
   CLAUDE.md, including proper handling of aspect actions, composite state
   during before/after timing, and pseudo states.

Example::

    >>> from pyfcstm.dsl import parse_with_grammar_entry
    >>> from pyfcstm.model import parse_dsl_node_to_state_machine
    >>> from pyfcstm.simulate import SimulationRuntime
    >>> dsl_code = '''
    ... def int counter = 0;
    ... state Root {
    ...     state A;
    ...     state B;
    ...     [*] -> A;
    ...     A -> B :: Go;
    ... }
    ... '''
    >>> ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
    >>> sm = parse_dsl_node_to_state_machine(ast)
    >>> runtime = SimulationRuntime(sm)
    >>> runtime.cycle()  # Enter initial state
    >>> runtime.cycle(['Root.A.Go'])  # Trigger transition
"""

from .runtime import SimulationRuntime
from .utils import get_event_name, get_func_name

__all__ = ['SimulationRuntime', 'get_event_name', 'get_func_name']
