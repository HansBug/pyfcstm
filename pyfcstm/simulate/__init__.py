"""
Simulation runtime for executing hierarchical finite state machines.

This package provides the runtime environment for executing state machines
parsed from the pyfcstm DSL. The runtime implements cycle-based execution
semantics where each cycle advances the state machine until it reaches a
stable stoppable state or terminates.

The module contains the following main components:

* :class:`SimulationRuntime` - Stateful runtime for executing hierarchical
  state machines with cycle-based semantics.
* :class:`SimulationRuntimeDfsError` - Exception raised when speculative
  validation exceeds safety limits.
* :func:`get_func_name` - Convert a lifecycle action to its readable path.
* :func:`is_state_resolve_event_path` - Check if a path string is definitely for State.resolve_event.

Key Concepts
------------

**State Types**:

* **Leaf State**: State with no children, can execute during actions
* **Composite State**: State with children, requires initial transitions
* **Pseudo State**: Leaf state that skips ancestor aspect actions
* **Stoppable State**: Leaf state (non-pseudo) where cycles can stabilize

**Lifecycle Actions**:

* **enter**: Executed when entering a state
* **during**: Executed while in a leaf state (each cycle)
* **exit**: Executed when leaving a state

**Aspect Actions**:

* **>> during before**: Executed before all descendant leaf during actions
* **>> during after**: Executed after all descendant leaf during actions
* Pseudo states skip ancestor aspect actions

**Transition Types**:

* **State-to-state**: ``A -> B`` (sibling transition)
* **Self-transition**: ``A -> A`` (exit then re-enter)
* **Initial transition**: ``[*] -> A`` (enter child from parent)
* **Exit transition**: ``A -> [*]`` (exit to parent)

Execution Semantics
-------------------

**Cycle Execution**:

A cycle advances the state machine until reaching a stable boundary:

1. From a leaf state, check transitions in declaration order
2. If a transition is enabled and validated, execute it
3. If no transition fires, execute the leaf state's during chain
4. Continue until reaching a stoppable state or terminating

**Transition Validation**:

When a stoppable state has an enabled transition, the runtime validates
that taking the transition can eventually reach another stoppable state
or terminate. This prevents cycles from getting stuck in non-stoppable
configurations.

**During Chain Execution** (for leaf states):

1. Execute ancestor ``>> during before`` actions (root to leaf)
2. Execute the leaf state's own ``during`` actions
3. Execute ancestor ``>> during after`` actions (leaf to root)

**Composite State Semantics**:

* ``during before``: Executes when entering composite from parent (``[*] -> Child``)
* ``during after``: Executes when exiting composite to parent (``Child -> [*]``)
* NOT executed during child-to-child transitions (``Child1 -> Child2``)

Error Handling
--------------

**SimulationRuntimeDfsError**:

Raised when speculative validation descends too deeply without converging.
This typically indicates an invalid state machine with unbounded execution
chains. The runtime enforces two safety limits:

* Maximum 1000 speculative steps per validation
* Maximum 64 structural stack depth

When validation exceeds these limits, the transition is rejected and the
cycle rolls back to the previous stable state.

**Rollback Behavior**:

If a cycle cannot reach a stoppable state, all variable changes are
rolled back and the runtime remains at the previous stable boundary.
For the initial cycle, rollback pins the runtime at the root boundary
in ``init_wait`` mode.

Example Usage
-------------

Basic cycle execution::

    >>> from pyfcstm.dsl import parse_with_grammar_entry
    >>> from pyfcstm.model import parse_dsl_node_to_state_machine
    >>> from pyfcstm.simulate import SimulationRuntime
    >>> dsl_code = '''
    ... def int counter = 0;
    ... state System {
    ...     state Idle {
    ...         during { counter = counter + 1; }
    ...     }
    ...     state Active {
    ...         during { counter = counter + 10; }
    ...     }
    ...     [*] -> Idle;
    ...     Idle -> Active :: Start;
    ... }
    ... '''
    >>> ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
    >>> sm = parse_dsl_node_to_state_machine(ast)
    >>> runtime = SimulationRuntime(sm)
    >>> runtime.cycle()  # Initialize and reach System.Idle
    >>> runtime.current_state.path
    ('System', 'Idle')
    >>> runtime.vars['counter']
    1
    >>> runtime.cycle(['System.Idle.Start'])  # Transition to Active
    >>> runtime.current_state.path
    ('System', 'Active')
    >>> runtime.vars['counter']
    11

Hierarchical execution with aspect actions::

    >>> dsl_code = '''
    ... def int log = 0;
    ... state Root {
    ...     >> during before { log = log + 1; }
    ...     >> during after { log = log + 100; }
    ...     state SubSystem {
    ...         during before { log = log + 10; }
    ...         state Active {
    ...             during { log = log + 50; }
    ...         }
    ...         [*] -> Active;
    ...     }
    ...     [*] -> SubSystem;
    ... }
    ... '''
    >>> ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
    >>> sm = parse_dsl_node_to_state_machine(ast)
    >>> runtime = SimulationRuntime(sm)
    >>> runtime.cycle()
    >>> runtime.vars['log']
    161  # Root.enter + SubSystem.enter + SubSystem.during_before(10) + Active.enter + Root.aspect_before(1) + Active.during(50) + Root.aspect_after(100)

Exit transitions and parent continuation::

    >>> dsl_code = '''
    ... def int x = 0;
    ... state System1 {
    ...     state A {
    ...         during { x = x + 1; }
    ...     }
    ...     [*] -> A;
    ...     A -> [*] :: Exit;
    ... }
    ... state System2 {
    ...     state B {
    ...         during { x = x + 10; }
    ...     }
    ...     [*] -> B;
    ... }
    ... [*] -> System1;
    ... System1 -> System2 :: Switch;
    ... '''
    >>> ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
    >>> sm = parse_dsl_node_to_state_machine(ast)
    >>> runtime = SimulationRuntime(sm)
    >>> runtime.cycle()
    >>> runtime.current_state.path
    ('System1', 'A')
    >>> runtime.cycle(['System1.A.Exit', 'Switch'])
    >>> runtime.current_state.path
    ('System2', 'B')

Validation preventing invalid transitions::

    >>> dsl_code = '''
    ... state Root {
    ...     state A;
    ...     state B {
    ...         [*] -> C : if [false];  # Blocked initial transition
    ...         state C;
    ...     }
    ...     [*] -> A;
    ...     A -> B :: Go;  # This transition will be rejected by validation
    ... }
    ... '''
    >>> ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
    >>> sm = parse_dsl_node_to_state_machine(ast)
    >>> runtime = SimulationRuntime(sm)
    >>> runtime.cycle()
    >>> runtime.cycle(['Root.A.Go'])  # Rejected - cannot reach stoppable state
    >>> runtime.current_state.path
    ('Root', 'A')  # Remains in A due to validation failure
"""

from .runtime import SimulationRuntime, SimulationRuntimeDfsError
from .utils import get_func_name, is_state_resolve_event_path
