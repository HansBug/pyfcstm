"""
Public simulation runtime interfaces for finite state machine execution.

This package exposes the runtime entry points used to execute
:class:`pyfcstm.model.StateMachine` instances after they have been parsed from
DSL source. The public API centers on :class:`SimulationRuntime`, with helper
functions for naming events and lifecycle actions in logs or tests.

The module contains the following main components:

* :class:`SimulationRuntime` - Stateful runtime for stepping and cycling a
  hierarchical state machine.
* :func:`get_event_name` - Convert an event object into its canonical path name.
* :func:`get_func_name` - Convert an action object into a readable path name.

.. note::
   The runtime documentation in this package describes the current implementation
   in [runtime.py](runtime.py), including the reviewed semantics documented in
   [SIMULATE_DESIGN.md](../../SIMULATE_DESIGN.md). In particular, cross-level
   transition behavior is explained according to the actual runtime rules rather
   than an idealized statechart model.

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
    >>> runtime.cycle()
    >>> runtime.cycle(['Root.A.Go'])
"""

from .runtime import SimulationRuntime
from .utils import get_event_name, get_func_name

__all__ = ['SimulationRuntime', 'get_event_name', 'get_func_name']
