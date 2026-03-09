"""
Simulation runtime for executing hierarchical finite state machines.

This package provides a cycle-based execution runtime for state machines parsed
from the pyfcstm DSL. Each cycle advances the state machine through transitions
and lifecycle actions until reaching a stable stoppable state or terminating.

The runtime supports hierarchical state machines with composite states, lifecycle
actions (enter/during/exit), aspect-oriented actions (>> during before/after), and
speculative validation to ensure transitions can reach valid stable states.

State types include leaf states (can execute during actions), composite states
(contain children and require initial transitions), pseudo states (skip ancestor
aspect actions), and stoppable states (non-pseudo leaf states where cycles stabilize).

Lifecycle actions execute at specific points: enter when entering a state, during
while in a leaf state each cycle, and exit when leaving a state. Aspect actions
(>> during before/after) execute before or after all descendant leaf during actions,
enabling cross-cutting concerns like logging or validation.

The runtime validates transitions speculatively before executing them, ensuring
they can eventually reach a stoppable state or terminate. If validation fails or
exceeds safety limits (1000 steps or 64 stack depth), the transition is rejected
and variables roll back to the previous stable state.

Abstract actions can be implemented by registering Python handlers that receive
read-only execution context. Handlers can be registered individually or organized
in classes using the @abstract_handler decorator for better state management.

Basic usage::

    from pyfcstm.dsl import parse_with_grammar_entry
    from pyfcstm.model import parse_dsl_node_to_state_machine
    from pyfcstm.simulate import SimulationRuntime

    ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
    sm = parse_dsl_node_to_state_machine(ast)
    runtime = SimulationRuntime(sm)

    # Execute cycles
    runtime.cycle()  # Initialize and execute first cycle
    runtime.cycle(['EventName'])  # Execute with events

    # Access state and variables
    current_state = runtime.current_state
    variables = runtime.vars

Abstract handler registration::

    from pyfcstm.simulate import abstract_handler

    class MyHandlers:
        @abstract_handler('System.Active.Init')
        def handle_init(self, ctx):
            print(f"State: {ctx.get_full_state_path()}")
            print(f"Counter: {ctx.get_var('counter')}")

    handlers = MyHandlers()
    runtime.register_handlers_from_object(handlers)
"""

from .context import ReadOnlyExecutionContext
from .decorators import abstract_handler
from .logging import get_logger
from .runtime import SimulationRuntime, SimulationRuntimeDfsError
from .utils import is_state_resolve_event_path
