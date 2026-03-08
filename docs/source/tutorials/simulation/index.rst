FCSTM Simulation Guide
===============================================

This guide provides a comprehensive introduction to simulating finite state machines defined in the FCSTM DSL. You'll learn how to execute state machines step-by-step, understand the execution semantics, handle events, implement abstract actions, and debug complex hierarchical state machines.

Overview
---------------------------------------

The pyfcstm simulation runtime provides a Python-based execution environment for FCSTM state machines. It allows you to:

- **Execute state machines interactively**: Run state machines cycle-by-cycle with full control
- **Trigger events dynamically**: Send events to trigger transitions during execution
- **Implement abstract actions**: Define custom Python handlers for abstract actions declared in DSL
- **Inspect runtime state**: Access current state, variables, and execution history
- **Debug complex logic**: Understand hierarchical execution order and aspect action behavior

The simulation runtime is ideal for:

- **Testing state machine logic**: Verify behavior before code generation
- **Prototyping**: Rapidly iterate on state machine designs
- **Education**: Learn FCSTM execution semantics through interactive examples
- **Debugging**: Trace execution flow in complex hierarchical state machines

Core Concepts
---------------------------------------

State Types
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The simulation runtime distinguishes between different state types:

- **Leaf State**: A state with no child states (can execute ``during`` actions)
- **Composite State**: A state containing child states (requires initial transitions)
- **Pseudo State**: A special leaf state that skips ancestor aspect actions
- **Stoppable State**: A leaf state (non-pseudo) where a cycle can end

Lifecycle Actions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

States can define three types of lifecycle actions:

- **enter**: Executed when entering a state
- **during**: Executed while remaining in a state (each cycle)
- **exit**: Executed when leaving a state

Aspect Actions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Aspect actions apply cross-cutting behavior to descendant states:

- **>> during before**: Executed before any descendant leaf state's ``during`` action
- **>> during after**: Executed after any descendant leaf state's ``during`` action
- Pseudo states skip ancestor aspect actions

Composite State Actions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Composite states can define special actions for boundary transitions:

- **during before** (without ``>>``): Executed when entering composite state from parent (``[*] -> Child``)
- **during after** (without ``>>``): Executed when exiting composite state to parent (``Child -> [*]``)
- **NOT executed** during child-to-child transitions (``Child1 -> Child2``)

Execution Semantics
---------------------------------------

Step Semantics
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A **step** executes a single transition or a single ``during`` action:

1. **If in a leaf state**:
   - Check all transitions from the current state in definition order
   - Execute the first transition whose guard condition is satisfied
   - If no transition fires, execute the current state's ``during`` action (including ancestor aspect actions)

2. **If in a composite state**:
   - Check all initial transitions (``[*] -> Child``) in definition order
   - Execute the first transition whose guard condition is satisfied

**Transition Execution Order**:

1. Execute source state's ``exit`` action
2. Execute transition's ``effect`` block
3. Execute target state's ``enter`` action
4. If target is composite, continue with initial transitions

Cycle Semantics
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A **cycle** executes until reaching a stable boundary:

1. Execute transitions and follow necessary chains until one of:
   - Reaching a **stoppable state** (leaf state, non-pseudo)
   - Confirming no stoppable state is reachable
   - State machine terminates

2. If a stoppable state is reached, execute its ``during`` action

**Key Points**:

- A cycle may execute multiple transitions (e.g., through pseudo states)
- A cycle always ends at a stoppable state or termination
- The ``during`` action executes only once per cycle at the final stoppable state

Hierarchical Execution Order
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Understanding execution order in hierarchical state machines is crucial. Consider this example:

.. code-block:: fcstm

   state System {
       >> during before { /* Aspect action */ }
       >> during after { /* Aspect action */ }

       state Parent {
           during before { /* Composite boundary action */ }
           during after { /* Composite boundary action */ }

           state Child {
               during { /* Leaf action */ }
           }

           [*] -> Child;
       }
   }

**Scenario 1: Initial Entry** (``System -> Parent -> Child``)

Entry phase:

1. ``System.enter``
2. ``Parent.enter``
3. ``Parent.during before`` (triggered by ``[*] -> Child``)
4. ``Child.enter``

During phase (each cycle while ``Child`` is active):

1. ``System >> during before`` (aspect action)
2. ``Child.during`` (leaf action)
3. ``System >> during after`` (aspect action)

Note: ``Parent.during before/after`` do NOT execute during the ``during`` phase.

**Scenario 2: Child-to-Child Transition** (``Child1 -> Child2``)

1. ``Child1.exit``
2. (Transition effect, if any)
3. ``Child2.enter``

CRITICAL: ``Parent.during before/after`` are NOT triggered during child-to-child transitions.

**Scenario 3: Exit from Composite State** (``Child -> [*]``)

1. ``Child.exit``
2. ``Parent.during after`` (triggered by ``Child -> [*]``)
3. ``Parent.exit``
4. ``System.exit``

Example State Machine
---------------------------------------

Throughout this guide, we'll use the following example state machine:

.. literalinclude:: example.fcstm
   :language: fcstm
   :caption: example.fcstm

This state machine demonstrates:

- **Variables**: ``counter``, ``error_count``, ``temperature``
- **Hierarchical states**: ``Active`` contains ``Processing`` and ``Waiting``
- **Lifecycle actions**: ``enter``, ``during``, ``exit``
- **Aspect actions**: ``>> during before`` with both abstract and concrete actions
- **Composite state actions**: ``Active.during before``
- **Transitions with guards**: ``Initializing -> Active : if [counter >= 10]``
- **Transitions with effects**: ``Active -> Idle :: Stop effect { counter = 0; }``
- **Forced transitions**: ``!* -> Error :: FatalError``
- **Abstract actions**: ``GlobalMonitor``, ``HardwareInit``

Basic Usage
---------------------------------------

Creating a Simulation Runtime
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The basic workflow for creating a simulation runtime:

1. Parse the DSL code into an AST
2. Convert the AST to a state machine model
3. Create a ``SimulationRuntime`` instance
4. Execute cycles

**Example**

.. literalinclude:: basic_usage.demo.py
   :language: python
   :caption: Basic simulation usage

Output:

.. literalinclude:: basic_usage.demo.py.txt
   :language: text

**Key Points**:

- ``runtime.cycle()``: Execute one complete cycle
- ``runtime.current_state``: Get the current state path (e.g., ``'System.Idle'``)
- ``runtime.vars``: Access state machine variables as a dictionary
- The first ``cycle()`` call initializes the state machine (follows initial transitions)

Accessing Runtime State
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``SimulationRuntime`` provides several properties for inspecting state:

.. code-block:: python

   # Current state path
   state_path = runtime.current_state  # e.g., 'System.Active.Processing'

   # Variable access
   counter_value = runtime.vars['counter']
   runtime.vars['counter'] = 10  # Modify variables

   # Check if terminated
   if runtime.is_terminated:
       print("State machine has terminated")

   # Get state object
   state_obj = runtime.get_current_state_object()
   print(f"State name: {state_obj.name}")
   print(f"Is leaf: {state_obj.is_leaf_state}")

Event Triggering
---------------------------------------

Events trigger transitions in the state machine. The simulation runtime supports dynamic event triggering.

Event Syntax in DSL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

FCSTM supports three event scoping mechanisms:

- **Local events** (``::``): Scoped to source state (e.g., ``StateA -> StateB :: LocalEvent``)
- **Chain events** (``:``): Scoped to parent state (e.g., ``StateA -> StateB : ChainEvent``)
- **Absolute events** (``/``): Scoped to root state (e.g., ``StateA -> StateB : /GlobalEvent``)

Triggering Events in Python
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pass event names to ``cycle()`` to trigger transitions:

.. literalinclude:: event_triggering.demo.py
   :language: python
   :caption: Event triggering example

Output:

.. literalinclude:: event_triggering.demo.py.txt
   :language: text

**Key Points**:

- Pass event names as a list to ``cycle()``: ``runtime.cycle(['Start'])``
- Event names are resolved based on scoping rules
- Multiple events can be provided: ``runtime.cycle(['Event1', 'Event2'])``
- Events are checked in the order provided
- If no event matches, the state machine executes the ``during`` action

Event Resolution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The runtime resolves event names to full event paths:

.. code-block:: python

   # For transition: Idle -> Active :: Start
   # Event is scoped to source state: System.Idle.Start
   runtime.cycle(['Start'])  # Matches System.Idle.Start

   # For transition: Idle -> Active : Start
   # Event is scoped to parent: System.Start
   runtime.cycle(['Start'])  # Matches System.Start

   # For transition: Idle -> Active : /Start
   # Event is scoped to root: System.Start
   runtime.cycle(['Start'])  # Matches System.Start

Abstract Actions
---------------------------------------

Abstract actions declare functions that must be implemented in Python. This allows you to integrate custom logic with the state machine.

Declaring Abstract Actions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the DSL, use the ``abstract`` keyword:

.. code-block:: fcstm

   state Active {
       enter abstract Init;
       during abstract Monitor;
       exit abstract Cleanup;
   }

Implementing Abstract Handlers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use the ``@abstract_handler`` decorator to implement handlers:

.. literalinclude:: abstract_handlers.demo.py
   :language: python
   :caption: Abstract action handlers

Output:

.. literalinclude:: abstract_handlers.demo.py.txt
   :language: text

**Key Points**:

- Use ``@abstract_handler('State.Path.ActionName')`` to register handlers
- Handler receives a ``context`` object with runtime information
- Register handlers with ``runtime.register_handlers_from_object(handler_obj)``
- Handlers can access variables via ``ctx.get_var('name')`` and ``ctx.set_var('name', value)``
- Handlers can inspect state via ``ctx.get_full_state_path()``

Handler Context API
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The context object passed to handlers provides:

.. code-block:: python

   @abstract_handler('System.Active.Monitor')
   def handle_monitor(self, ctx):
       # Get current state path
       state_path = ctx.get_full_state_path()  # e.g., 'System.Active'

       # Access variables
       counter = ctx.get_var('counter')
       ctx.set_var('counter', counter + 1)

       # Get state object
       state = ctx.get_state()
       print(f"State name: {state.name}")

       # Access runtime
       runtime = ctx.get_runtime()
       print(f"Current state: {runtime.current_state}")

Hierarchical Execution
---------------------------------------

Understanding how actions execute in hierarchical state machines is essential for correct behavior.

Aspect Actions Example
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: hierarchy_execution.demo.py
   :language: python
   :caption: Hierarchical execution order

Output:

.. literalinclude:: hierarchy_execution.demo.py.txt
   :language: text

**Explanation**:

- **Cycle 1** (initialization): Executes ``Parent.during before`` (100) during entry because ``[*] -> Child``
- **Cycle 2** (during phase): Executes ``>> during before`` (1) + ``Child.during`` (10)
- **Cycle 3** (during phase): Same as cycle 2
- ``Parent.during before`` does NOT execute during the ``during`` phase

Execution Order Summary
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Entry Phase** (from parent):

1. ``State.enter``
2. ``State.during before`` (if entering from parent via ``[*] -> Child``)
3. ``Child.enter``

**During Phase** (each cycle):

1. Ancestor ``>> during before`` actions (root to leaf)
2. Leaf state ``during`` action
3. Ancestor ``>> during after`` actions (leaf to root)

**Exit Phase** (to parent):

1. ``Child.exit``
2. ``State.during after`` (if exiting to parent via ``Child -> [*]``)
3. ``State.exit``

**Child-to-Child Transition**:

1. ``Child1.exit``
2. (Transition effect)
3. ``Child2.enter``
4. NO ``during before/after`` execution

Pseudo States
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pseudo states skip ancestor aspect actions:

.. code-block:: fcstm

   state System {
       >> during before { counter = counter + 1; }

       pseudo state SpecialState {
           during { counter = counter + 10; }
       }
   }

When ``SpecialState`` is active:

- ``System >> during before`` is NOT executed
- Only ``SpecialState.during`` executes

Advanced Features
---------------------------------------

Multiple Cycles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Execute multiple cycles in a loop:

.. code-block:: python

   # Execute 10 cycles
   for i in range(10):
       runtime.cycle()
       print(f"Cycle {i+1}: State={runtime.current_state}, Counter={runtime.vars['counter']}")

   # Execute until termination
   while not runtime.is_terminated:
       runtime.cycle()

Conditional Execution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use guards to control transitions:

.. code-block:: python

   # State machine with guards
   dsl_code = """
   def int counter = 0;

   state System {
       [*] -> Idle;

       state Idle {
           during { counter = counter + 1; }
       }

       state Active;

       Idle -> Active : if [counter >= 5];
   }
   """

   runtime = SimulationRuntime(sm)

   # Execute until transition fires
   while runtime.current_state == 'System.Idle':
       runtime.cycle()
       print(f"Counter: {runtime.vars['counter']}")

   print(f"Transitioned to: {runtime.current_state}")

Debugging Tips
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**1. Print state and variables after each cycle**:

.. code-block:: python

   runtime.cycle()
   print(f"State: {runtime.current_state}")
   print(f"Variables: {runtime.vars}")

**2. Trace execution with abstract handlers**:

.. code-block:: python

   @abstract_handler('System.Active.Monitor')
   def trace_monitor(self, ctx):
       print(f"[TRACE] Monitor called at {ctx.get_full_state_path()}")
       print(f"[TRACE] Variables: {dict(ctx.get_runtime().vars)}")

**3. Inspect state objects**:

.. code-block:: python

   state_obj = runtime.get_current_state_object()
   print(f"State: {state_obj.name}")
   print(f"Is leaf: {state_obj.is_leaf_state}")
   print(f"Is pseudo: {state_obj.is_pseudo}")
   print(f"Transitions: {len(state_obj.transitions)}")

**4. Check transition guards manually**:

.. code-block:: python

   for transition in state_obj.transitions:
       if transition.guard:
           print(f"Guard: {transition.guard.to_dsl()}")

Best Practices
---------------------------------------

State Machine Design
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Keep states focused**: Each state should have a clear, single responsibility
- **Use hierarchical states**: Group related states under composite states
- **Minimize aspect actions**: Use aspect actions sparingly for cross-cutting concerns
- **Document abstract actions**: Add comments to abstract action declarations

Simulation Testing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Test initialization**: Verify the state machine reaches the correct initial state
- **Test all transitions**: Ensure all transitions fire under correct conditions
- **Test guards**: Verify guard conditions work as expected
- **Test effects**: Check that transition effects modify variables correctly
- **Test termination**: Ensure the state machine terminates when expected

Handler Implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Keep handlers simple**: Handlers should be lightweight and focused
- **Avoid side effects**: Minimize external state modifications in handlers
- **Use context API**: Access runtime state through the context object
- **Log handler execution**: Add logging for debugging complex interactions

Performance Considerations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Limit cycle count**: Avoid infinite loops by checking termination conditions
- **Optimize guards**: Keep guard expressions simple for faster evaluation
- **Minimize aspect actions**: Aspect actions execute on every cycle
- **Use pseudo states**: Skip aspect actions when not needed

Common Pitfalls
---------------------------------------

Aspect Action Confusion
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem**: Expecting ``during before/after`` (without ``>>``) to execute during the ``during`` phase.

**Solution**: Remember that composite state ``during before/after`` only execute during entry/exit transitions (``[*] -> Child`` or ``Child -> [*]``), NOT during the ``during`` phase.

Event Scoping Issues
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem**: Events not triggering transitions due to incorrect scoping.

**Solution**: Understand event scoping:

- ``::`` creates state-specific events
- ``:`` creates parent-scoped events
- ``/`` creates root-scoped events

Variable Initialization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem**: Variables not initialized before use.

**Solution**: Always define variables at the top of the DSL with initial values:

.. code-block:: fcstm

   def int counter = 0;
   def float temperature = 25.0;

Missing Abstract Handlers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Problem**: Abstract actions declared but not implemented, causing runtime errors.

**Solution**: Implement all abstract handlers before running the simulation:

.. code-block:: python

   # Check for missing handlers
   runtime = SimulationRuntime(sm)
   handlers = MyHandlers()
   runtime.register_handlers_from_object(handlers)

   # This will raise an error if handlers are missing
   runtime.cycle()

Next Steps
---------------------------------------

- Explore the :doc:`../visualization/index` to visualize your state machines
- Learn about :doc:`../dsl/index` for advanced DSL features
- Check out :doc:`../render/index` for code generation from state machines
- Read :doc:`../cli/index` for command-line simulation tools

Summary
---------------------------------------

This guide covered:

- Core concepts: state types, lifecycle actions, aspect actions, execution semantics
- Basic usage: creating runtimes, executing cycles, accessing state
- Event triggering: dynamic event handling and scoping
- Abstract actions: implementing custom handlers with the ``@abstract_handler`` decorator
- Hierarchical execution: understanding execution order in nested states
- Advanced features: multiple cycles, conditional execution, debugging
- Best practices: design, testing, handler implementation, performance
- Common pitfalls: aspect actions, event scoping, variable initialization

The simulation runtime provides a powerful environment for testing, prototyping, and understanding FCSTM state machines before code generation.