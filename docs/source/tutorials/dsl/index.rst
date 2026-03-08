PyFCSTM DSL Syntax Tutorial
========================================

.. contents:: Table of Contents
   :local:
   :depth: 3

Overview
----------------------------------------------------

The PyFCSTM Domain Specific Language (DSL) provides a comprehensive syntax for defining hierarchical finite state machines (Harel Statecharts) with expressions, conditions, and lifecycle actions. This tutorial covers all language constructs, semantic rules, execution models, and best practices for writing correct and efficient DSL programs.

What You'll Learn
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Complete DSL syntax and grammar rules
- How hierarchical state machines execute
- Event scoping and namespace resolution
- Expression system and operators
- Lifecycle actions and aspect-oriented programming
- Real-world examples and design patterns

Language Structure
----------------------------------------------------

Program Organization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A complete DSL program consists of optional variable definitions followed by a single root state definition:

.. code-block:: fcstm

   program ::= def_assignment* state_definition EOF

The top-level structure ensures every state machine has exactly one root state that may contain nested substates and transitions.

.. note::
   The parser processes your DSL file in multiple phases:

   1. **Lexical Analysis**: Tokenizes the input into keywords, identifiers, operators, and literals
   2. **Syntactic Analysis**: Builds an Abstract Syntax Tree (AST) following the grammar rules
   3. **Semantic Validation**: Validates variable references, state names, and type consistency
   4. **Model Construction**: Converts the AST into an executable state machine model

Variable Definitions
----------------------------------------------------

Syntax
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Variable definitions declare typed variables with initial values using the ``def`` keyword:

.. code-block:: fcstm

   def_assignment ::= 'def' ('int'|'float') ID '=' init_expression ';'

.. important::
   Variables are global to the entire state machine and can be accessed from any state, transition, or expression. The DSL supports two primitive types:

   - **int**: 32-bit signed integers, supporting decimal (``42``), hexadecimal (``0xFF``), and binary (``0b1010``) literals
   - **float**: Double-precision floating-point numbers, supporting standard (``3.14``) and scientific notation (``1e-6``)

   All variables must be initialized at declaration time. The initial expression can include:

   - Literal values (``0``, ``3.14``, ``0xFF``)
   - Mathematical constants (``pi``, ``E``, ``tau``)
   - Arithmetic expressions (``3.14 * 2``, ``10 + 5``)
   - Mathematical functions (``sin(0)``, ``sqrt(16)``)

Correct Usage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Integer Variables:**

.. code-block:: fcstm

   def int counter = 0;              // Simple initialization
   def int max_attempts = 5;         // Constant value
   def int flags = 0xFF;             // Hexadecimal literal
   def int mask = 0b11110000;        // Binary literal
   def int computed = 10 * 5 + 3;    // Expression initialization

**Float Variables:**

.. code-block:: fcstm

   def float temperature = 25.5;     // Decimal notation
   def float pi_value = pi;          // Mathematical constant
   def float ratio = 3.14 * 2;       // Expression initialization
   def float scientific = 1.5e-3;    // Scientific notation
   def float computed = sqrt(16.0);  // Function call

**Annotated Example:**

.. code-block:: fcstm

   // System state variables
   def int system_state = 0;         // 0=init, 1=running, 2=error
   def int error_count = 0;          // Track error occurrences

   // Sensor readings
   def float temperature = 20.0;     // Current temperature in Celsius
   def float target_temp = 22.0;     // Desired temperature

   // Control outputs
   def int heating_power = 0;        // Heating power (0-100%)
   def int fan_speed = 0;            // Fan speed (0-3)

   // Bit flags for system status
   def int status_flags = 0x00;      // Bit 0: heating, Bit 1: cooling
                                     // Bit 2: fan, Bit 3: error

Semantic Rules
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Variable definitions must follow these semantic constraints:

1. **Unique Names**: Each variable name must be unique within the program scope
2. **Type Consistency**: Initial expressions must evaluate to values compatible with the declared type
3. **Expression Validity**: Initial expressions can only reference mathematical constants and literals (not other variables)
4. **Declaration Order**: Variables must be declared before the root state definition

.. tip::
   **Why These Rules?**

   - **Unique Names**: Prevents ambiguity in variable references throughout the state machine
   - **Type Consistency**: Ensures type safety and prevents runtime errors in generated code
   - **Expression Validity**: Simplifies initialization and ensures deterministic startup state
   - **Declaration Order**: Maintains clear separation between data definitions and behavior definitions

Common Errors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Incorrect Usage:**

.. code-block:: fcstm

   // ERROR: Duplicate variable names
   def int x = 1;
   def float x = 2.0;  // Semantic error: 'x' already defined

   // ERROR: Undefined reference in initialization
   def int y = unknown_var;  // Semantic error: 'unknown_var' not defined

   // ERROR: Referencing another variable
   def int a = 10;
   def int b = a;  // Semantic error: cannot reference variables in initialization

**Correct Alternative:**

.. code-block:: fcstm

   // Use unique names
   def int x_int = 1;
   def float x_float = 2.0;

   // Initialize with literals or constants
   def int y = 0;

   // Assign variable values in state actions
   def int a = 10;
   def int b = 0;

   state Init {
       enter {
           b = a;  // Assign in lifecycle action
       }
   }

State Definitions
----------------------------------------------------

.. note::
   A finite state machine (FSM) is a computational model that can be in exactly one state at any given time. The machine transitions between states in response to events, executing actions during these transitions. Hierarchical state machines (Harel Statecharts) extend this concept by allowing states to contain nested substates, enabling modular and scalable designs.

Syntax Types
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The DSL supports two fundamental types of state definitions:

.. code-block:: fcstm

   state_definition ::= leafStateDefinition | compositeStateDefinition
   leafStateDefinition ::= ['pseudo'] 'state' ID [named STRING] ';'
   compositeStateDefinition ::= ['pseudo'] 'state' ID [named STRING] '{' state_inner_statement* '}'

.. tip::
   **Key Differences:**

   - **Leaf States**: Terminal states with no internal structure; represent atomic operational modes
   - **Composite States**: Container states with nested substates; represent hierarchical decomposition

Leaf States
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Leaf states represent terminal states with no internal structure. They are the fundamental building blocks of state machines.

**Correct Usage:**

.. code-block:: fcstm

   state Idle;                      // Simple leaf state
   state Running;                   // Another leaf state
   state Error;                     // Error state

   // Leaf state with display name
   state Running named "System Running";

   // Pseudo leaf state (skips ancestor aspect actions)
   pseudo state SpecialState;

.. tip::
   **When to Use Leaf States:**

   - Representing atomic operational modes (Idle, Running, Error)
   - Final states in a hierarchical decomposition
   - States with simple, non-decomposable behavior

**Annotated Example:**

.. code-block:: fcstm

   state TrafficLight {
       // Leaf states representing light colors
       state Red;      // Stop signal
       state Yellow;   // Caution signal
       state Green;    // Go signal

       [*] -> Red;
       Red -> Green :: TimerExpired;
       Green -> Yellow :: TimerExpired;
       Yellow -> Red :: TimerExpired;
   }

Composite States
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Composite states contain nested substates, transitions, and lifecycle actions. They enable hierarchical decomposition of complex behaviors.

**Correct Usage:**

.. code-block:: fcstm

   state Machine {
       // Nested substates
       state Off;
       state On {
           state Slow;
           state Fast;

           [*] -> Slow;
           Slow -> Fast :: SpeedUp;
           Fast -> Slow :: SlowDown;
       }

       // Transitions between top-level states
       [*] -> Off;
       Off -> On : if [power_switch == 1];
       On -> Off : if [power_switch == 0];
   }

.. important::
   When a composite state is active, exactly one of its child states is also active. This creates a hierarchical execution context:

   1. **Entry**: When entering a composite state, the entry transition (``[*] -> ChildState``) determines which child becomes active
   2. **During**: While active, the composite state's ``during before/after`` actions execute around the child state's actions
   3. **Exit**: When leaving a composite state, the active child state exits first, then the composite state exits

**Annotated Example:**

.. code-block:: fcstm

   state PowerManagement {
       // Composite state lifecycle actions
       enter {
           // Executed when entering PowerManagement from outside
           power_level = 0;
       }

       during before {
           // Executed when entering a child state from outside
           // NOT executed during child-to-child transitions
           monitor_counter = monitor_counter + 1;
       }

       during after {
           // Executed when exiting to outside from a child state
           // NOT executed during child-to-child transitions
           cleanup_flag = 1;
       }

       exit {
           // Executed when leaving PowerManagement to outside
           power_level = 0;
       }

       // Child states
       state LowPower {
           during {
               power_level = 10;
           }
       }

       state NormalPower {
           during {
               power_level = 50;
           }
       }

       state HighPower {
           during {
               power_level = 100;
           }
       }

       [*] -> LowPower;
       LowPower -> NormalPower :: Increase;
       NormalPower -> HighPower :: Increase;
       HighPower -> NormalPower :: Decrease;
       NormalPower -> LowPower :: Decrease;
   }

Pseudo States
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pseudo states are special states (leaf or composite) that skip ancestor aspect actions. They are useful for implementing special behaviors that need to bypass cross-cutting concerns.

**Syntax:**

.. code-block:: fcstm

   pseudo state StateName;
   pseudo state StateName { ... }

.. note::
   Normal states execute ancestor aspect actions (``>> during before/after``) defined in parent states. Pseudo states skip these aspect actions, providing a way to opt out of cross-cutting behaviors.

**Comparison Example:**

.. literalinclude:: pseudo_state_demo.fcstm
    :language: fcstm
    :linenos:

**Execution Comparison:**

When ``RegularState`` is active:

1. Root ``>> during before`` executes (``aspect_counter += 1``)
2. ``RegularState.during`` executes (``aspect_counter += 10``)
3. Root ``>> during after`` executes (``aspect_counter += 100``)
4. **Total increment per cycle**: 111

When ``SpecialState`` (pseudo) is active:

1. Root ``>> during before`` **SKIPPED**
2. ``SpecialState.during`` executes (``aspect_counter += 10``)
3. Root ``>> during after`` **SKIPPED**
4. **Total increment per cycle**: 10

.. tip::
   **When to Use Pseudo States:**

   - Implementing exception handlers that bypass normal monitoring
   - Creating special states for testing or debugging
   - Optimizing performance-critical states by skipping overhead

Named States
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

States can have display names for documentation and visualization purposes:

.. code-block:: fcstm

   state Running named "System Running";
   state Error named "Error State - Requires Manual Reset";
   state Init named "Initialization Phase";

The display name is used in PlantUML diagrams and generated documentation, while the state ID is used in code generation.

Semantic Rules
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

State definitions must adhere to these semantic constraints:

1. **Unique Names**: State names must be unique within their containing scope (but can be reused in different scopes)
2. **Entry Transitions**: Composite states must have at least one entry transition (``[*] -> state``)
3. **State References**: All transition targets must reference existing states in the current scope
4. **Hierarchical Consistency**: Nested states follow proper parent-child relationships
5. **Aspect Restrictions**: ``during before/after`` (without ``>>``) only apply to composite states

.. tip::
   **Why These Rules?**

   - **Unique Names**: Prevents ambiguity in transition targets and event scoping
   - **Entry Transitions**: Ensures deterministic behavior when entering composite states
   - **State References**: Prevents dangling transitions and ensures connectivity
   - **Hierarchical Consistency**: Maintains proper state machine structure
   - **Aspect Restrictions**: Enforces correct lifecycle semantics for leaf vs. composite states

Common Errors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Incorrect Usage:**

.. code-block:: fcstm

   // ERROR: Missing entry transition
   state Container {
       state A;
       state B;
       A -> B :: Event;  // No [*] -> A or [*] -> B
   }

   // ERROR: Duplicate state names in same scope
   state Root {
       state Child;
       state Child;  // Semantic error: duplicate name
   }

   // ERROR: Invalid transition target
   state Root {
       state A;
       [*] -> A;
       A -> B :: Event;  // Semantic error: B doesn't exist
   }

   // ERROR: during before/after on leaf state
   state LeafState {
       during before {  // Semantic error: leaf states can't have aspects
           x = 1;
       }
   }

**Correct Alternative:**

.. code-block:: fcstm

   // Provide entry transition
   state Container {
       state A;
       state B;
       [*] -> A;  // Entry transition required
       A -> B :: Event;
   }

   // Use unique names
   state Root {
       state ChildA;
       state ChildB;
   }

   // Define all referenced states
   state Root {
       state A;
       state B;
       [*] -> A;
       A -> B :: Event;
   }

   // Use plain during for leaf states
   state LeafState {
       during {  // Correct: no aspect keywords
           x = 1;
       }
   }

Transition Definitions
----------------------------------------------------

.. note::
   Transitions define how the state machine moves from one state to another in response to events or conditions. Each transition can have:

   - **Source State**: The state from which the transition originates
   - **Target State**: The state to which the transition leads
   - **Event**: Optional trigger that activates the transition
   - **Guard Condition**: Optional boolean expression that must be true for the transition to fire
   - **Effect**: Optional actions executed during the transition

Transition Types
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The DSL supports three types of transitions with distinct syntax patterns:

.. code-block:: fcstm

   transition_definition ::= entryTransitionDefinition | normalTransitionDefinition | exitTransitionDefinition

Entry Transitions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Entry transitions define the initial state when entering a composite state. They use the pseudo-state ``[*]`` as the source.

**Syntax:** ``[*] -> target_state [: chain_id|:: event_name] [if [condition]] [effect { operations }] ';'``

**Correct Usage:**

.. code-block:: fcstm

   [*] -> Idle;                                    // Simple entry
   [*] -> Running : startup_event;                 // Entry with chain event
   [*] -> Running :: startup_event;                // Entry with local event
   [*] -> Active : if [initialized == 0x1];        // Entry with guard
   [*] -> Ready effect { counter = 0; };           // Entry with effect
   [*] -> Running : if [mode == 1] effect {        // Entry with guard and effect
       counter = 0;
       status = 1;
   };

.. note::
   When a composite state is entered from outside, the entry transition determines which child state becomes active. The guard condition (if present) is evaluated, and if true, the effect (if present) is executed before entering the target state.

Normal Transitions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Normal transitions connect two named states within the same scope.

**Syntax:** ``from_state -> to_state [: chain_id|:: event_name] [if [condition]] [effect { operations }] ';'``

**Correct Usage:**

.. code-block:: fcstm

   Idle -> Running;                                // Simple transition
   Slow -> Fast : speed_up;                        // Transition with chain event
   Slow -> Fast :: speed_up;                       // Transition with local event
   Active -> Inactive : if [timeout > 100];        // Transition with guard
   Processing -> Complete effect {                 // Transition with effect
       result = output;
       status = 1;
   };
   Running -> Idle : if [stop_requested] effect {  // Guard and effect
       cleanup_flag = 1;
   };

.. note::
   Normal transitions are evaluated during the "during" phase of the source state. When the event is triggered (if specified) and the guard condition is true (if specified), the transition fires:

   1. Source state's exit action executes
   2. Transition effect executes (if present)
   3. Target state's enter action executes

Exit Transitions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Exit transitions define how to leave a composite state to its parent. They use the pseudo-state ``[*]`` as the target.

**Syntax:** ``from_state -> [*] [: chain_id|:: event_name] [if [condition]] [effect { operations }] ';'``

**Correct Usage:**

.. code-block:: fcstm

   Error -> [*];                                   // Simple exit
   Complete -> [*] : finish_event;                 // Exit with event
   Running -> [*] : if [shutdown_requested];       // Exit with guard
   Active -> [*] effect {                          // Exit with effect
       cleanup_flag = 0x1;
   };
   Processing -> [*] : if [done] effect {          // Guard and effect
       result = final_value;
   };

.. note::
   Exit transitions allow a child state to signal completion and return control to the parent state. The parent state can then transition to another state or exit itself.

Forced Transitions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Forced transitions are a **syntactic sugar** that automatically expands to multiple normal transitions. They are useful for defining transitions from multiple states to a common target without repetitive code, especially for error handling or emergency situations.

**Syntax:**

.. code-block:: fcstm

   // Forced transition from specific state
   ! from_state -> to_state [: chain_id|:: event_name] [if [condition]] ';'

   // Forced exit from specific state
   ! from_state -> [*] [: chain_id|:: event_name] [if [condition]] ';'

   // Forced transition from ALL substates (wildcard)
   ! * -> to_state [: chain_id|:: event_name] [if [condition]] ';'

   // Forced exit from ALL substates
   ! * -> [*] [: chain_id|:: event_name] [if [condition]] ';'

.. important::
   Forced transitions are a **syntactic sugar** that expands during model construction. When you write:

   .. code-block:: fcstm

      state Parent {
          ! * -> ErrorHandler :: CriticalError;

          state Child1;
          state Child2;
      }

   The parser automatically generates normal transitions from **all substates**:

   .. code-block:: fcstm

      // Expanded transitions (generated automatically):
      Child1 -> ErrorHandler : CriticalError;
      Child2 -> ErrorHandler : CriticalError;

   **Important**: These are **normal transitions** - they execute exit actions just like any other transition.

**Key Characteristics:**

1. **Syntactic Sugar**: Expands to multiple normal transitions during model construction
2. **Wildcard Expansion**: ``! *`` generates transitions from all substates in the current scope
3. **Hierarchical Propagation**: Forced transitions propagate to nested substates recursively
4. **Shared Event Object**: All expanded transitions share the **same event object**
5. **No Effect Blocks**: Forced transitions cannot have effect blocks (syntax limitation)
6. **Normal Execution**: Exit actions execute normally - forced transitions are just regular transitions

.. tip::
   **When to Use Forced Transitions:**

   - **Avoid Repetitive Code**: Define one transition instead of many identical ones
   - **Error Handling**: Transition from any state to error handler
   - **Emergency Shutdown**: Transition from all states to shutdown state
   - **Timeout Handling**: Handle timeouts uniformly across multiple states

.. code-block:: fcstm

   state System {
       // Force transition from any state to error handler
       ! * -> ErrorHandler :: CriticalError;

       // Force transition from specific state
       ! Running -> SafeMode :: EmergencyStop;

       // Force exit from any state
       ! * -> [*] :: FatalError;

       // With guard condition
       ! * -> ErrorHandler : if [error_code > 100];

       state Running {
           exit {
               // This exit action WILL execute when transitioning
               cleanup_flag = 1;
           }
       }

       state ErrorHandler;
   }

**When to Use Forced Transitions:**

- **Avoid Repetitive Code**: Define one transition instead of many identical ones
- **Error Handling**: Transition from any state to error handler
- **Emergency Shutdown**: Transition from all states to shutdown state
- **Timeout Handling**: Handle timeouts uniformly across multiple states

**Complete Example:**

.. literalinclude:: forced_transitions.fcstm
    :language: fcstm
    :linenos:

**Visualization:**

.. figure:: forced_transitions.fcstm.puml.svg
   :width: 80%
   :align: center
   :alt: Forced Transitions Example

**Expansion Behavior:**

When ``! * -> ErrorHandler :: CriticalError`` is defined in ``System``, it expands to:

.. code-block:: fcstm

   // From direct children
   Running -> ErrorHandler :: CriticalError;
   Idle -> ErrorHandler :: CriticalError;
   SafeMode -> ErrorHandler :: CriticalError;
   ErrorHandler -> ErrorHandler :: CriticalError;

   // Propagates to nested children (Running.Processing, Running.Waiting)
   // Inside Running state, generates:
   Processing -> [*] : /CriticalError;  // Exit to parent, then parent transitions
   Waiting -> [*] : /CriticalError;

**Event Sharing:**

All expanded transitions from a single forced transition definition share the **same event object**. This means:

.. code-block:: fcstm

   state System {
       ! * -> ErrorHandler :: CriticalError;

       state A;
       state B;
       state C;
   }

   // All these transitions use the SAME event object:
   // A -> ErrorHandler :: CriticalError
   // B -> ErrorHandler :: CriticalError
   // C -> ErrorHandler :: CriticalError
   // When you trigger CriticalError, ALL matching transitions can fire

.. warning::
   1. **Normal Transitions**: Expanded transitions are normal transitions - exit actions execute
   2. **Event Sharing**: All expanded transitions share the same event object
   3. **No Effect Blocks**: Forced transitions cannot have effect blocks (use target state's enter action)
   4. **Scope Limitation**: ``! *`` applies to direct substates, but propagates recursively
   5. **Event Scoping**: Event scoping rules (``:`` vs ``::``) apply normally

**Common Errors:**

.. code-block:: fcstm

   // ERROR: Cannot have effect block on forced transition
   ! * -> ErrorHandler :: Error effect {  // Syntax error
       error_code = 1;
   };

   // ERROR: Forced transition must reference existing states
   ! * -> NonExistentState :: Error;  // Semantic error

**Correct Alternative:**

.. code-block:: fcstm

   // Use enter action in target state for initialization
   state ErrorHandler {
       enter {
           error_code = 1;  // Initialize in target state
       }
   }

   ! * -> ErrorHandler :: Error;  // Correct: no effect block

Event Definitions
----------------------------------------------------

Events are the core mechanism that triggers state transitions. In finite state machines, state transitions are typically driven by external events—such as user input, sensor signals, timer expiration, or system messages. Events provide the state machine with the ability to respond to external stimuli, enabling it to change behavior based on the current state and received events.

In the PyFCSTM DSL, events can be defined in two ways:

1. **Implicit Definition**: Events are automatically created when referenced directly in transitions
2. **Explicit Definition**: Events are pre-declared using the ``event`` keyword, optionally with display names

Explicit Event Definitions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Events can be explicitly defined within a state scope using the ``event`` keyword:

**Syntax:**

.. code-block:: fcstm

   event_definition ::= 'event' ID ('named' STRING)? ';'

**Examples:**

.. code-block:: fcstm

   event StartEvent;                              // Simple event definition
   event ErrorOccurred named "Error Occurred";    // Event with display name
   event UserInput named "User Input Received";   // Event with descriptive name

**Purpose of Explicit Event Definitions:**

Explicit event definitions serve several important purposes:

1. **Documentation**: Explicitly declare events used within a state scope for better code clarity and maintainability
2. **Visualization**: The ``named`` attribute provides human-readable display names for PlantUML diagrams and documentation generation
3. **Consistency**: Similar to state definitions with ``named``, event definitions support visualization and documentation tools

.. important::
   **Relationship with Transition Events:**

   Explicit event definitions and transition events are part of the **same event system**. When you define an event explicitly, it can be referenced in transitions within the same scope. The events are unified - there is no distinction between "explicitly defined events" and "transition events" at runtime.

**Complete Example:**

.. code-block:: fcstm

   state System {
       // Explicit event definitions with display names
       event Start named "System Start";
       event Stop named "System Stop";
       event Pause named "System Pause";
       event Resume named "System Resume";

       state Idle;
       state Running;
       state Paused;

       [*] -> Idle;
       Idle -> Running : Start;      // References the explicitly defined Start event
       Running -> Idle : Stop;       // References the explicitly defined Stop event
       Running -> Paused : Pause;    // References the explicitly defined Pause event
       Paused -> Running : Resume;   // References the explicitly defined Resume event
   }

.. note::
   **Key Points:**

   - Explicit event definitions are **optional** - events can be used in transitions without explicit definition
   - The ``named`` attribute is the primary benefit, providing display names for visualization (PlantUML, state diagrams)
   - Events defined explicitly follow the same scoping rules as transition events (see Event Scoping section below)
   - Explicit definitions improve code readability, self-documentation, and integration with visualization tools
   - The ``named`` attribute works exactly like the ``named`` attribute for states - it provides a human-readable label

Event Scoping
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In hierarchical state machines, events need a namespace to avoid naming conflicts.

.. important::
   Consider this scenario:

   .. code-block:: fcstm

      state Root {
          state A;
          state B;
          state C;

          [*] -> A;
          A -> B : Event;  // Which Event?
          B -> C : Event;  // Same Event or different?
      }

   Should both transitions use the same event or different events? The DSL provides **three scoping mechanisms** to handle this.

Scoping Mechanisms
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The DSL supports three ways to specify event scope:

1. **Local Events** (``::``): Scoped to the source state's namespace
2. **Chain Events** (``:``): Scoped to the parent state's namespace
3. **Absolute Events** (``/``): Scoped to the root state's namespace

All three mechanisms are equivalent to using absolute paths, just with different starting points.

Local Events (`::` operator)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Local events use the ``::`` operator and are scoped to the **source state's namespace**.

**Syntax:** ``StateA -> StateB :: EventName;``

.. note::
   The event is created in the source state's namespace. Each source state gets its own event.

**Example:**

.. code-block:: fcstm

   state Root {
       state A;
       state B;

       [*] -> A;
       A -> B :: E;     // Creates event: Root.A.E
       B -> A :: E;     // Creates event: Root.B.E (DIFFERENT from above)
   }

**Equivalent Absolute Path:**

.. code-block:: fcstm

   // A -> B :: E  is equivalent to:
   A -> B : /A.E

   // B -> A :: E  is equivalent to:
   B -> A : /B.E

.. tip::
   **When to Use:**

   - Each transition needs its own unique event
   - Avoid naming conflicts between similar transitions
   - State-specific events that shouldn't be shared

Chain Events (`:` operator)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Chain events use the ``:`` operator and are scoped to the **parent state's namespace**.

**Syntax:** ``StateA -> StateB : EventName;``

.. note::
   The event is created in the parent state's namespace. Multiple transitions in the same scope can share the event.

**Example:**

.. code-block:: fcstm

   state Root {
       state A;
       state B;
       state C;

       [*] -> A;
       A -> B : E;      // Creates event: Root.E
       B -> C : E;      // Uses SAME event: Root.E
   }

**Equivalent Absolute Path:**

.. code-block:: fcstm

   // A -> B : E  is equivalent to:
   A -> B : /E

   // B -> C : E  is equivalent to:
   B -> C : /E

.. tip::
   **When to Use:**

   - Multiple transitions should respond to the same event
   - Coordinating transitions across sibling states
   - Shared events within a scope

Absolute Events (`/` prefix)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Absolute events use the ``/`` prefix and are scoped to the **root state's namespace**.

**Syntax:** ``StateA -> StateB : /EventName;`` or ``StateA -> StateB : /Path.To.EventName;``

.. note::
   The event path is resolved from the root state, allowing explicit control over event location.

**Example:**

.. code-block:: fcstm

   state Root {
       state ModuleA {
           state A1;
           state A2;

           [*] -> A1;
           A1 -> A2 : /GlobalEvent;  // Uses Root.GlobalEvent
       }

       state ModuleB {
           state B1;
           state B2;

           [*] -> B1;
           B1 -> B2 : /GlobalEvent;  // Uses SAME Root.GlobalEvent
       }

       [*] -> ModuleA;
   }

**Equivalent Absolute Path:**

.. code-block:: fcstm

   // Already absolute - no conversion needed
   A1 -> A2 : /GlobalEvent  // Root.GlobalEvent
   B1 -> B2 : /GlobalEvent  // Root.GlobalEvent (SAME event)

.. tip::
   **When to Use:**

   - Cross-module communication
   - Global events that should be accessible from anywhere
   - Explicit control over event location
   - Avoiding ambiguity in deeply nested states

Complete Comparison Example
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Here's a comprehensive example demonstrating all three scoping mechanisms:

.. literalinclude:: event_scoping_complete.fcstm
    :language: fcstm
    :linenos:

**Visualization:**

.. figure:: event_scoping_complete.fcstm.puml.svg
   :width: 90%
   :align: center
   :alt: Complete Event Scoping Example

**Event Resolution Table:**

.. list-table::
   :header-rows: 1
   :widths: 40 30 30

   * - Transition Syntax
     - Event Scope
     - Absolute Path Equivalent
   * - ``A1 -> A2 :: LocalEvent``
     - Source state (A1)
     - ``A1 -> A2 : /ModuleA.A1.LocalEvent``
   * - ``A2 -> A1 : ChainEvent``
     - Parent state (ModuleA)
     - ``A2 -> A1 : /ModuleA.ChainEvent``
   * - ``ModuleA -> Target : /GlobalEvent``
     - Root state (System)
     - Already absolute: ``/GlobalEvent``
   * - ``B1 -> B2 :: LocalEvent``
     - Source state (B1)
     - ``B1 -> B2 : /ModuleB.B1.LocalEvent``
   * - ``B2 -> B1 : ChainEvent``
     - Parent state (ModuleB)
     - ``B2 -> B1 : /ModuleB.ChainEvent``
   * - ``ModuleB -> Target : /GlobalEvent``
     - Root state (System)
     - Already absolute: ``/GlobalEvent``

**Key Observations:**

1. **Local events** (``::``): Each source state gets its own event
   - ``ModuleA.A1.LocalEvent`` ≠ ``ModuleB.B1.LocalEvent``

2. **Chain events** (``:``): Each parent scope gets its own event
   - ``ModuleA.ChainEvent`` ≠ ``ModuleB.ChainEvent``

3. **Absolute events** (``/``): All transitions share the same event
   - ``ModuleA -> Target : /GlobalEvent`` = ``ModuleB -> Target : /GlobalEvent``

.. seealso::
   You can also use dot notation with absolute paths to reference events in specific states:

   .. code-block:: fcstm

      state Root {
          state A {
              state A1;
              state A2;

              [*] -> A1;
          }

          state B {
              state B1;
              state B2;

              [*] -> B1;
              // Reference event from A's namespace
              B1 -> B2 : /A.SpecificEvent;  // Uses Root.A.SpecificEvent
          }

          [*] -> A;
      }

   This allows fine-grained control over event location in the hierarchy.

Guard Conditions and Effects
----------------------------------------------------

Guard Conditions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Guard conditions are boolean expressions that control whether a transition can fire. They are enclosed in square brackets after the ``if`` keyword.

**Syntax:** ``StateA -> StateB : if [condition];``

**Supported Operators:**

- **Comparison**: ``<``, ``>``, ``<=``, ``>=``, ``==``, ``!=``
- **Logical**: ``&&``, ``||``, ``!``, ``and``, ``or``, ``not``
- **Bitwise**: ``&``, ``|``, ``^``
- **Arithmetic**: ``+``, ``-``, ``*``, ``/``, ``%``, ``**``

**Examples:**

.. code-block:: fcstm

   // Simple comparison
   Idle -> Active : if [counter >= 10];

   // Logical AND
   Normal -> Critical : if [battery_level < 10 && charging_state == 0];

   // Logical OR
   LowPower -> Critical : if [temperature > 80 || error_count > 5];

   // Bitwise operations
   Charging -> Normal : if [(battery_level >= 90) && (charging_state & 0x01)];

   // Complex expression
   StateA -> StateB : if [(temp > 25.0) && (flags & 0xFF) == 0x01];

Transition Effects
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Transition effects are blocks of operations executed during a transition, after the source state exits but before the target state enters.

**Syntax:** ``StateA -> StateB effect { operations };``

**Examples:**

.. code-block:: fcstm

   // Simple effect
   Idle -> Running effect {
       counter = 0;
   };

   // Multiple operations
   Critical -> Charging effect {
       charging_state = 1;
       error_count = 0;
       temperature = 25;
   };

   // Complex expressions
   Processing -> Complete effect {
       result = sin(angle) * radius;
       flags = flags | 0x01;
       counter = counter + 1;
   };

Combined Guards and Effects
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Transitions can have both guard conditions and effects:

.. code-block:: fcstm

   // Guard and effect
   Charging -> Normal : if [battery_level >= 100] effect {
       charging_state = 0;
       battery_level = 100;
   };

   // Complex guard and effect
   Running -> Idle : if [(timeout > 100) && (error_count == 0)] effect {
       cleanup_flag = 1;
       status = 0;
   };

Complete Example
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here's a comprehensive example demonstrating guards and effects:

.. literalinclude:: guards_and_effects.fcstm
    :language: fcstm
    :linenos:

**Visualization:**

.. figure:: guards_and_effects.fcstm.puml.svg
   :width: 80%
   :align: center
   :alt: Guards and Effects Example

Semantic Rules
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Transitions must satisfy these semantic constraints:

1. **State Existence**: Both source and target states must exist in the current scope
2. **Variable Validity**: All variables in conditions and effects must be declared
3. **Expression Types**: Guard conditions must evaluate to boolean values
4. **Entry Requirements**: Composite states require at least one entry transition
5. **Effect Scope**: Effects can only assign to declared variables

**Why These Rules?**

- **State Existence**: Prevents dangling transitions
- **Variable Validity**: Ensures all references are resolvable
- **Expression Types**: Maintains type safety in guard evaluation
- **Entry Requirements**: Ensures deterministic composite state entry
- **Effect Scope**: Prevents undefined behavior in generated code

Common Errors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Incorrect Usage:**

.. code-block:: fcstm

   // ERROR: References to undefined states
   StateA -> UndefinedState :: Event;  // Semantic error

   // ERROR: Missing entry transition
   state Container {
       state A;
       state B;
       A -> B :: Event;  // No [*] -> A or [*] -> B
   }

   // ERROR: Invalid variable in guard
   StateA -> StateB : if [undefined_var > 10];  // Semantic error

   // ERROR: Non-boolean guard
   StateA -> StateB : if [counter + 10];  // Semantic error: not boolean

   // ERROR: Invalid assignment target
   StateA -> StateB effect {
       undefined_var = 10;  // Semantic error
   };

**Correct Alternative:**

.. code-block:: fcstm

   // Define all states
   state Root {
       state StateA;
       state StateB;
       [*] -> StateA;
       StateA -> StateB :: Event;
   }

   // Provide entry transition
   state Container {
       state A;
       state B;
       [*] -> A;  // Required
       A -> B :: Event;
   }

   // Use declared variables
   def int counter = 0;
   state Root {
       state StateA;
       state StateB;
       [*] -> StateA;
       StateA -> StateB : if [counter > 10];  // Valid
   }

   // Use boolean expressions
   StateA -> StateB : if [counter > 10];  // Valid: comparison returns boolean

   // Assign to declared variables
   def int result = 0;
   state Root {
       state StateA;
       state StateB;
       [*] -> StateA;
       StateA -> StateB effect {
           result = 10;  // Valid
       };
   }

Expression System
----------------------------------------------------

**How Expressions Work:**

The DSL provides a comprehensive expression system for mathematical computations, logical operations, and conditional logic. Expressions can appear in:

- Variable initializations (``def int x = expression;``)
- Guard conditions (``if [expression]``)
- Transition effects (``variable = expression;``)
- Lifecycle actions (``variable = expression;``)

Expression Hierarchy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The DSL supports comprehensive expression types for mathematical and logical operations:

.. code-block:: fcstm

   init_expression ::= conditional_expression
   num_expression ::= conditional_expression
   cond_expression ::= conditional_expression
   conditional_expression ::= logical_or_expression ['?' expression ':' expression]
   logical_or_expression ::= logical_and_expression [('||' | 'or') logical_and_expression]*
   logical_and_expression ::= bitwise_or_expression [('&&' | 'and') bitwise_or_expression]*
   bitwise_or_expression ::= bitwise_xor_expression ['|' bitwise_xor_expression]*
   bitwise_xor_expression ::= bitwise_and_expression ['^' bitwise_and_expression]*
   bitwise_and_expression ::= equality_expression ['&' equality_expression]*
   equality_expression ::= relational_expression [('==' | '!=') relational_expression]*
   relational_expression ::= shift_expression [('<' | '>' | '<=' | '>=') shift_expression]*
   shift_expression ::= additive_expression [('<<' | '>>') additive_expression]*
   additive_expression ::= multiplicative_expression [('+' | '-') multiplicative_expression]*
   multiplicative_expression ::= power_expression [('*' | '/' | '%') power_expression]*
   power_expression ::= unary_expression ['**' unary_expression]*
   unary_expression ::= ['+' | '-' | '!' | 'not'] primary_expression
   primary_expression ::= literal | variable | function_call | '(' expression ')'

Literal Values
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Integer Literals:**

.. code-block:: fcstm

   def int decimal = 42;           // Decimal notation
   def int hex = 0xFF;             // Hexadecimal (0x prefix)
   def int binary = 0b11110000;    // Binary (0b prefix)
   def int octal = 0o755;          // Octal (0o prefix)

**Float Literals:**

.. code-block:: fcstm

   def float standard = 3.14;      // Standard notation
   def float scientific = 1.5e-3;  // Scientific notation (0.0015)
   def float large = 1E10;         // Large numbers (10000000000)
   def float pi_const = pi;        // Mathematical constant
   def float e_const = E;          // Euler's number
   def float tau_const = tau;      // Tau (2*pi)

**Boolean Literals:**

.. code-block:: fcstm

   // True values (case-insensitive)
   true, True, TRUE

   // False values (case-insensitive)
   false, False, FALSE

Operators
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Arithmetic Operators (by precedence, highest to lowest):**

1. **Parentheses**: ``()`` - Grouping
2. **Unary**: ``+``, ``-`` - Positive, negative
3. **Power**: ``**`` - Exponentiation
4. **Multiplicative**: ``*``, ``/``, ``%`` - Multiply, divide, modulo
5. **Additive**: ``+``, ``-`` - Addition, subtraction

**Comparison Operators:**

- **Relational**: ``<``, ``>``, ``<=``, ``>=``
- **Equality**: ``==``, ``!=``

**Logical Operators:**

- **Unary**: ``!``, ``not`` - Logical NOT
- **Binary**: ``&&``, ``and`` - Logical AND
- **Binary**: ``||``, ``or`` - Logical OR

**Bitwise Operators:**

- **Bitwise AND**: ``&``
- **Bitwise OR**: ``|``
- **Bitwise XOR**: ``^``
- **Left Shift**: ``<<``
- **Right Shift**: ``>>``

**Operator Precedence Example:**

.. code-block:: fcstm

   // Without parentheses (follows precedence)
   result = 2 + 3 * 4;              // Result: 14 (multiplication first)
   result = 2 ** 3 + 1;             // Result: 9 (power first)
   result = 10 / 2 + 3;             // Result: 8 (division first)

   // With parentheses (overrides precedence)
   result = (2 + 3) * 4;            // Result: 20
   result = 2 ** (3 + 1);           // Result: 16
   result = 10 / (2 + 3);           // Result: 2

Arithmetic vs Logical Expression Separation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. danger::
   The fcstm DSL strictly separates arithmetic expressions (``num_expression``) from logical/boolean expressions (``cond_expression``). Unlike common high-level languages, you **cannot mix** arithmetic and logical operations freely.

   **Key Rules:**

   1. **Assignments require arithmetic expressions** - You cannot assign boolean results directly
   2. **Guard conditions require boolean expressions** - You cannot use arithmetic values as conditions
   3. **Comparison operators bridge the two** - They take arithmetic operands and produce boolean results

**Common Errors:**

.. code-block:: fcstm

   // ERROR: Cannot assign boolean expression to variable
   result = (x > 10);               // Syntax error: boolean in arithmetic context
   result = (flag1 && flag2);       // Syntax error: logical operation in assignment

   // ERROR: Cannot use arithmetic expression as condition
   StateA -> StateB : if [counter]; // Syntax error: arithmetic in boolean context
   StateA -> StateB : if [x + 5];   // Syntax error: arithmetic in boolean context

**Correct Usage:**

.. code-block:: fcstm

   // Use ternary operator to convert boolean to arithmetic
   result = (x > 10) ? 1 : 0;       // Valid: ternary returns arithmetic value
   result = (flag1 && flag2) ? 1 : 0;  // Valid: converts boolean to int

   // Use comparison operators in guard conditions
   StateA -> StateB : if [counter > 0];    // Valid: comparison returns boolean
   StateA -> StateB : if [x + 5 > 10];     // Valid: arithmetic in comparison

   // Bitwise operations work in arithmetic context
   result = flags & 0x01;           // Valid: bitwise returns arithmetic value
   StateA -> StateB : if [(flags & 0x01) != 0];  // Valid: compare bitwise result

.. tip::
   **Why This Matters:**

   This separation ensures type safety and prevents ambiguous expressions. In languages like C, ``if (x + 5)`` is valid (non-zero is true), but in fcstm DSL you must be explicit: ``if [x + 5 > 0]``. This makes state machine logic clearer and prevents subtle bugs.

Mathematical Functions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The DSL provides extensive mathematical function support:

**Trigonometric Functions:**

.. code-block:: fcstm

   // Basic trigonometry
   result = sin(angle);             // Sine
   result = cos(angle);             // Cosine
   result = tan(angle);             // Tangent

   // Inverse trigonometry
   result = asin(value);            // Arcsine
   result = acos(value);            // Arccosine
   result = atan(value);            // Arctangent

   // Hyperbolic functions
   result = sinh(value);            // Hyperbolic sine
   result = cosh(value);            // Hyperbolic cosine
   result = tanh(value);            // Hyperbolic tangent

**Exponential and Logarithmic:**

.. code-block:: fcstm

   result = exp(x);                 // e^x
   result = log(x);                 // Natural logarithm (base e)
   result = log10(x);               // Logarithm base 10
   result = log2(x);                // Logarithm base 2

**Other Mathematical Functions:**

.. code-block:: fcstm

   result = sqrt(x);                // Square root
   result = abs(x);                 // Absolute value
   result = ceil(x);                // Ceiling (round up)
   result = floor(x);               // Floor (round down)
   result = round(x);               // Round to nearest integer

Conditional Expressions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Conditional expressions use ternary operator syntax for inline conditional logic.

**Syntax:** ``(condition) ? true_value : false_value``

.. important::
   The condition MUST be enclosed in parentheses.

**Examples:**

.. code-block:: fcstm

   // Simple conditional
   result = (x > 0) ? 1 : -1;

   // With variables
   status = (temperature > 25.0) ? 1 : 0;

   // Nested conditionals
   level = (temp > 30) ? 3 : ((temp > 20) ? 2 : 1);

   // With complex conditions
   value = (counter >= 10 && flags & 0x01) ? 100 : 0;

   // With expressions in branches
   result = (mode == 1) ? (base * 2) : (base / 2);

**Common Error:**

.. warning::
   .. code-block:: fcstm

      // ERROR: Missing parentheses around condition
      result = x > 0 ? 1 : -1;  // Syntax error

      // CORRECT: Parentheses required
      result = (x > 0) ? 1 : -1;

Complete Expression Example
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here's a comprehensive example demonstrating all expression capabilities:

.. literalinclude:: expression_demo.fcstm
    :language: fcstm
    :linenos:

**Visualization:**

.. figure:: expression_demo.fcstm.puml.svg
   :width: 80%
   :align: center
   :alt: Expression System Demonstration

Semantic Rules
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Expressions must follow these semantic constraints:

1. **Variable Declarations**: All referenced variables must be declared
2. **Type Consistency**: Operations must be performed on compatible types
3. **Function Arguments**: Mathematical functions require appropriate argument types
4. **Boolean Context**: Conditional guards must evaluate to boolean values
5. **Operator Compatibility**: Operators must be used with compatible operand types

**Why These Rules?**

- **Variable Declarations**: Prevents undefined behavior
- **Type Consistency**: Ensures type safety in generated code
- **Function Arguments**: Prevents runtime errors in mathematical operations
- **Boolean Context**: Maintains semantic correctness in control flow
- **Operator Compatibility**: Ensures meaningful operations

Common Errors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Incorrect Usage:**

.. code-block:: fcstm

   // ERROR: Undefined variable reference
   result = unknown_var + 10;  // Semantic error

   // ERROR: Type mismatch (mixing incompatible types)
   // Note: DSL is dynamically typed, but some operations may fail

   // ERROR: Invalid function arguments
   result = sqrt(-1);  // May cause runtime error

   // ERROR: Malformed conditional (missing parentheses)
   result = x > 0 ? 1 : -1;  // Syntax error

**Correct Alternative:**

.. code-block:: fcstm

   // Declare all variables
   def int result = 0;
   def int known_var = 10;

   state Example {
       enter {
           result = known_var + 10;  // Valid
       }
   }

   // Use appropriate function arguments
   def float value = 16.0;
   state Example {
       enter {
           result = sqrt(value);  // Valid: positive argument
       }
   }

   // Use parentheses in conditionals
   result = (x > 0) ? 1 : -1;  // Valid

Lifecycle Actions
----------------------------------------------------

.. note::
   **How Lifecycle Actions Work:**

   Lifecycle actions define behavior that executes at specific points in a state's lifetime:

   - **Enter Actions**: Execute once when entering a state
   - **During Actions**: Execute repeatedly while a state is active
   - **Exit Actions**: Execute once when leaving a state

   For composite states, lifecycle actions can have **aspects** (``before``/``after``) that control execution order relative to child states.

Action Types
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

States support three lifecycle phases with corresponding action definitions:

.. code-block:: fcstm

   enter_definition ::= enterOperations | enterAbstractFunc | enterRefFunc
   during_definition ::= duringOperations | duringAbstractFunc
   exit_definition ::= exitOperations | exitAbstractFunc | exitRefFunc

   enterOperations ::= 'enter' [ID] '{' operation* '}'
   enterAbstractFunc ::= 'enter' 'abstract' ID [MULTILINE_COMMENT]
   enterRefFunc ::= 'enter' [ID] 'ref' chain_id

   duringOperations ::= 'during' ['before'|'after'] [ID] '{' operation* '}'
   duringAbstractFunc ::= 'during' ['before'|'after'] 'abstract' ID [MULTILINE_COMMENT]

   exitOperations ::= 'exit' [ID] '{' operation* '}'
   exitAbstractFunc ::= 'exit' 'abstract' ID [MULTILINE_COMMENT]
   exitRefFunc ::= 'exit' [ID] 'ref' chain_id

Enter Actions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Enter actions execute when a state is entered from outside.

**Concrete Operations:**

.. code-block:: fcstm

   state Active {
       // Simple enter action
       enter {
           counter = 0;
           status_flag = 0x1;
       }

       // Named enter action (for reference)
       enter InitializeSystem {
           counter = 0;
           flags = 0xFF;
           temperature = 25.0;
       }
   }

**Abstract Functions:**

Abstract enter actions declare functions that must be implemented in generated code:

.. code-block:: fcstm

   state Active {
       // Simple abstract enter
       enter abstract initialize_system;

       // Abstract enter with documentation
       enter abstract setup_resources /*
           Initialize system resources and peripherals.
           This function must allocate memory, open files,
           and configure hardware interfaces.
           TODO: Implement in generated code framework
       */
   }

**Reference Actions:**

Reference actions reuse enter actions from other states:

.. code-block:: fcstm

   state BaseState {
       enter CommonInit {
           counter = 0;
           flags = 0xFF;
       }
   }

   state DerivedState {
       // Reuse BaseState's enter action
       enter ref BaseState.CommonInit;

       // Can also reference global actions
       enter ref /GlobalInit;
   }

.. important::
   ``ref`` is an **action reuse mechanism**, not a state reference and not an event reference.
   It resolves to a previously named lifecycle action under a state scope. The target may be a
   named ``enter``, ``during``, ``exit``, or ``>> during`` action, including an abstract action.
   Relative paths are resolved from the current state path, while ``/`` starts from the root state.

.. tip::
   Use ``ref`` when several states should share the same lifecycle behavior and you want one source
   of truth for that action body or abstract hook. Prefer absolute paths for cross-state reuse to
   avoid ambiguity. Use ``abstract`` instead when the action is only a contract to be implemented in
   generated code rather than a reuse of an existing named action.

During Actions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

During actions execute while a state is active. The behavior differs between leaf and composite states.

**Leaf State During Actions:**

Leaf states use plain ``during`` without aspect keywords:

.. code-block:: fcstm

   state Running {
       // Executes every cycle while Running is active
       during {
           heartbeat_counter = heartbeat_counter + 1;
           temperature = temperature + 0.1;
       }
   }

**Composite State During Actions:**

Composite states MUST use ``before`` or ``after`` aspects:

.. code-block:: fcstm

   state Parent {
       // Executes when entering a child from outside
       // NOT during child-to-child transitions
       during before {
           monitor_counter = monitor_counter + 1;
       }

       // Executes when exiting to outside from a child
       // NOT during child-to-child transitions
       during after {
           cleanup_flag = 1;
       }

       state Child1;
       state Child2;

       [*] -> Child1;
       Child1 -> Child2 :: Switch;  // during before/after NOT triggered
       Child2 -> [*];
   }

**Abstract During Actions:**

.. code-block:: fcstm

   state Processing {
       // Leaf state abstract during
       during abstract process_data;

       // With documentation
       during abstract process_data /*
           Process incoming data packets.
           TODO: Implement data processing logic
       */
   }

   state Container {
       // Composite state abstract during with aspect
       during before abstract pre_process /*
           Pre-processing before child state execution.
           TODO: Implement pre-processing logic
       */

       during after abstract post_process;

       state Child;
       [*] -> Child;
   }

Exit Actions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Exit actions execute when leaving a state to outside.

**Concrete Operations:**

.. code-block:: fcstm

   state Active {
       exit {
           save_state = current_value;
           cleanup_flag = 0x1;
           status = 0;
       }

       // Named exit action
       exit CleanupResources {
           flags = 0x00;
           counter = 0;
       }
   }

**Abstract Functions:**

.. code-block:: fcstm

   state Active {
       exit abstract cleanup_resources;

       exit abstract finalize_operations /*
           Clean up resources before exit.
           Release memory, close files, and shutdown hardware.
           TODO: Implement in generated code framework
       */
   }

**Reference Actions:**

.. code-block:: fcstm

   state BaseState {
       exit CommonCleanup {
           cleanup_flag = 1;
           counter = 0;
       }
   }

   state DerivedState {
       exit ref BaseState.CommonCleanup;
   }

Aspect Actions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Aspect actions apply to **all descendant leaf states** using the ``>>`` prefix.

**Syntax:**

.. code-block:: fcstm

   state Root {
       // Executes before EVERY descendant leaf state's during action
       >> during before {
           global_counter = global_counter + 1;
       }

       // Executes after EVERY descendant leaf state's during action
       >> during after {
           global_counter = global_counter + 100;
       }

       state Child {
           state GrandChild {
               during {
                   local_counter = local_counter + 10;
               }
           }

           [*] -> GrandChild;
       }

       [*] -> Child;
   }

**Execution Order for GrandChild:**

1. ``Root >> during before`` (``global_counter += 1``)
2. ``GrandChild.during`` (``local_counter += 10``)
3. ``Root >> during after`` (``global_counter += 100``)

Hierarchical Execution Order
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Understanding execution order in hierarchical state machines is crucial. Here's a complete example:

.. literalinclude:: hierarchy_execution.fcstm
    :language: fcstm
    :linenos:

**Visualization:**

.. figure:: hierarchy_execution.fcstm.puml.svg
   :width: 80%
   :align: center
   :alt: Hierarchical Execution Order

.. important::
   **Execution Scenarios:**

   **Scenario 1: Initial Entry** (``HierarchyDemo -> Parent -> ChildA``)

   1. ``HierarchyDemo.enter`` (if defined)
   2. ``Parent.enter`` (if defined)
   3. ``Parent.during before`` executes (``execution_log += 100``)
   4. ``ChildA.enter`` (if defined)

   **Scenario 2: During Phase** (while ``ChildA`` is active, each cycle)

   1. ``HierarchyDemo >> during before`` (``execution_log += 1000``)
   2. ``Parent >> during before`` (``execution_log += 10``)
   3. ``ChildA.during`` (``execution_log += 1``)
   4. ``Parent >> during after`` (``execution_log += 90``)
   5. ``HierarchyDemo >> during after`` (``execution_log += 9000``)

   **Total per cycle**: 10101

   **Scenario 3: Child-to-Child Transition** (``ChildA -> ChildB :: Switch``)

   1. ``ChildA.exit`` (if defined)
   2. Transition effect (if any)
   3. ``ChildB.enter`` (if defined)

   **CRITICAL**: ``Parent.during before/after`` are **NOT** executed!

   **Scenario 4: Exit from Composite State** (``ChildB -> [*] :: Exit``)

   1. ``ChildB.exit`` (if defined)
   2. ``Parent.during after`` executes (``execution_log += 900``)
   3. ``Parent.exit`` (if defined)
   4. ``HierarchyDemo.exit`` (if defined)

**Lifecycle Flow Diagrams:**

.. list-table::
   :widths: 55 45
   :align: center

   * - .. figure:: composite_state_lifecycle.puml.svg
          :width: 100%
          :align: center
          :alt: Lifecycle of Composite States

     - .. figure:: leaf_state_lifecycle.puml.svg
          :width: 100%
          :align: center
          :alt: Lifecycle of Leaf States

Abstract and Reference Actions Example
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here's a complete example demonstrating abstract functions and action references:

.. literalinclude:: abstract_reference_demo.fcstm
    :language: fcstm
    :linenos:

**Visualization:**

.. figure:: abstract_reference_demo.fcstm.puml.svg
   :width: 80%
   :align: center
   :alt: Abstract and Reference Actions

Semantic Rules
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Lifecycle actions must adhere to these constraints:

1. **Variable Validity**: All referenced variables must be declared
2. **Aspect Restrictions**: ``before`` and ``after`` aspects only apply to composite states
3. **Assignment Targets**: Only declared variables can be assigned values
4. **Expression Types**: Assignment expressions must be type-compatible
5. **Reference Validity**: Referenced actions must exist in the specified state

.. tip::
   **Why These Rules?**

   - **Variable Validity**: Prevents undefined behavior
   - **Aspect Restrictions**: Enforces correct lifecycle semantics
   - **Assignment Targets**: Ensures all assignments are valid
   - **Expression Types**: Maintains type safety
   - **Reference Validity**: Prevents dangling references

Common Errors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. warning::
   **Incorrect Usage:**

   .. code-block:: fcstm

      // ERROR: Undefined variable in action
      state Example {
          enter {
              undefined_var = 10;  // Semantic error
          }
      }

      // ERROR: Aspect on leaf state
      state LeafState {
          during before {  // Semantic error: leaf states can't have aspects
              x = 1;
          }
      }

      // ERROR: Plain during on composite state
      state CompositeState {
          state Child;
          [*] -> Child;

          during {  // Semantic error: composite states need before/after
              x = 1;
          }
      }

      // ERROR: Invalid reference
      state Example {
          enter ref NonExistentState.Action;  // Semantic error
      }

**Correct Alternative:**

.. code-block:: fcstm

   // Declare all variables
   def int result = 0;

   state Example {
       enter {
           result = 10;  // Valid
       }
   }

   // Use plain during for leaf states
   state LeafState {
       during {  // Correct
           result = 1;
       }
   }

   // Use aspects for composite states
   state CompositeState {
       state Child;
       [*] -> Child;

       during before {  // Correct
           result = 1;
       }
   }

   // Reference existing actions
   state BaseState {
       enter CommonInit {
           result = 0;
       }
   }

   state DerivedState {
       enter ref BaseState.CommonInit;  // Valid
   }

Real-World Example: Smart Thermostat
----------------------------------------------------

To demonstrate all DSL features in a realistic context, here's a comprehensive smart thermostat controller implementation:

.. literalinclude:: thermostat_example.fcstm
    :language: fcstm
    :linenos:

**Visualization:**

.. figure:: thermostat_example.fcstm.puml.svg
   :width: 90%
   :align: center
   :alt: Smart Thermostat State Machine

.. tip::
   **Key Design Patterns Demonstrated:**

   1. **Hierarchical Decomposition**: ``OperationalMode`` contains multiple sub-modes (Idle, Heating, Cooling, AutoMode)
   2. **Aspect-Oriented Programming**: Global ``>> during before/after`` for logging and display updates
   3. **Proportional Control**: Heating/cooling power calculated based on temperature difference
   4. **Automatic Mode Switching**: ``AutoMode`` intelligently switches between heating, cooling, and idle
   5. **Error Handling**: Transitions to ``ErrorState`` on abnormal conditions
   6. **Maintenance Scheduling**: Automatic transition to maintenance after 1000 cycles
   7. **Abstract Functions**: Hardware-specific operations declared as abstract for platform implementation

**Execution Flow Example:**

Starting from ``Initializing``:

1. System performs self-test (abstract function)
2. If ``error_code == 0``, transitions to ``OperationalMode.Idle``
3. ``OperationalMode.during before`` executes (increments ``runtime_hours``)
4. While in ``Idle``:
   - Global ``>> during before`` logs system state
   - ``Idle.during`` increments ``maintenance_counter``
   - Global ``>> during after`` updates display
5. If ``current_temp < target_temp - 1``, transitions to ``Heating``
6. While in ``Heating``:
   - ``Heating.during`` calculates proportional heating power
   - If ``current_temp >= target_temp``, transitions back to ``Idle``
7. After 1000 cycles, transitions to ``Maintenance``

Comment Styles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The DSL supports multiple comment formats for documentation:

**Line Comments:**

.. code-block:: fcstm

   // C++ style line comment
   # Python style line comment

   def int counter = 0;  // Inline comment
   def int flags = 0xFF; # Another inline comment

**Block Comments:**

.. code-block:: fcstm

   /*
    * Multi-line block comment
    * Used for detailed documentation
    */

**Abstract Function Documentation:**

.. code-block:: fcstm

   enter abstract InitializeHardware /*
       Initialize hardware peripherals and sensors.

       This function must:
       1. Configure GPIO pins
       2. Initialize SPI/I2C interfaces
       3. Calibrate sensors
       4. Verify hardware connectivity

       Returns: 0 on success, error code on failure
       TODO: Implement in generated code framework
   */

Documentation Best Practices
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Variable Documentation:**

.. code-block:: fcstm

   // System state variables
   def int system_state = 0;         // 0=init, 1=running, 2=error
   def int error_count = 0;          // Number of errors since startup

   // Sensor readings (in SI units)
   def float temperature = 20.0;     // Temperature in Celsius
   def float pressure = 101.325;     // Pressure in kPa

   // Control outputs (0-100 range)
   def int heating_power = 0;        // Heating power percentage
   def int cooling_power = 0;        // Cooling power percentage

**State Documentation:**

.. code-block:: fcstm

   state System {
       // Initialization phase - runs once at startup
       state Initializing {
           enter {
               // Reset all system variables to safe defaults
               error_count = 0;
               system_state = 0;
           }
       }

       // Normal operation - main system loop
       state Running {
           // Active processing state
           state Active {
               during {
                   // Increment heartbeat counter for watchdog
                   heartbeat = heartbeat + 1;
               }
           }

           // Idle state - low power mode
           state Idle;

           [*] -> Active;
       }

       [*] -> Initializing;
       Initializing -> Running : if [error_count == 0];
   }

**Transition Documentation:**

.. code-block:: fcstm

   // Transition to low power mode when battery is low
   // and no critical tasks are active
   Normal -> LowPower : if [
       (battery_level < 30) &&
       (charging_state == 0) &&
       (critical_task_active == 0)
   ] effect {
       // Reduce system clock frequency
       clock_divider = 8;
       // Disable non-essential peripherals
       peripheral_enable = 0x01;
   };

Semantic Validation Rules
----------------------------------------------------

Comprehensive Validation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The DSL parser performs extensive semantic validation during the parsing process:

**Variable Validation:**

1. Unique variable names across the program
2. All referenced variables must be declared
3. Type consistency in assignments and expressions
4. Valid initialization expressions

**State Validation:**

1. Unique state names within each scope
2. Valid state references in all transitions
3. Required entry transitions for composite states
4. Proper hierarchical nesting

**Expression Validation:**

1. Well-formed mathematical and logical expressions
2. Valid function calls with appropriate arguments
3. Proper operator precedence and associativity
4. Type compatibility in operations

**Structural Validation:**

1. Proper nesting of composite states
2. Valid lifecycle action placement
3. Correct transition connectivity
4. Aspect action restrictions

Error Handling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The parser provides detailed error messages for common mistakes:

**Syntax Errors:**

- Malformed expressions and statements
- Missing punctuation and keywords
- Invalid token sequences
- Incorrect operator usage

**Semantic Errors:**

- Undefined variable or state references
- Type mismatches in operations
- Structural inconsistencies
- Invalid lifecycle action placement

**Example Error Messages:**

.. code-block:: fcstm

   Error: Undefined variable 'unknown_var' at line 15
   Error: Duplicate state name 'Active' in scope 'System' at line 23
   Error: Missing entry transition for composite state 'Container' at line 45
   Error: Invalid aspect 'before' on leaf state 'Running' at line 67

Summary
----------------------------------------------------

This tutorial has covered the complete PyFCSTM DSL syntax, including:

- **Variable Definitions**: Typed variables with initialization expressions
- **State Definitions**: Leaf states, composite states, pseudo states, and named states
- **Transitions**: Entry, normal, exit, and forced transitions with guards and effects
- **Forced Transitions**: Syntactic sugar that expands to multiple normal transitions with shared events
- **Event Scoping**: Three mechanisms - local events (``::``), chain events (``:``), and absolute events (``/``)
- **Event Namespaces**: Understanding how events are resolved in hierarchical state machines
- **Expressions**: Comprehensive operator support and mathematical functions
- **Lifecycle Actions**: Enter, during, and exit actions with aspect-oriented programming
- **Hierarchical Execution**: Execution order in nested states with composite and leaf states
- **Abstract Functions**: Declaring platform-specific implementations
- **Reference Actions**: Reusing actions across states
- **Comments**: Line and block comments for documentation

.. important::
   **Key Concepts:**

   - **Hierarchical State Machines**: States can contain nested substates, enabling modular design
   - **Aspect-Oriented Programming**: ``>> during before/after`` actions apply to all descendant leaf states
   - **Composite State Lifecycle**: ``during before/after`` execute only on entry/exit, not during child-to-child transitions
   - **Event Namespacing**: Three scoping mechanisms (``::`` for local, ``:`` for chain, ``/`` for absolute)
   - **Event Resolution**: All event scoping mechanisms are equivalent to absolute paths with different starting points
   - **Semantic Validation**: Comprehensive validation ensures correct state machine definitions

.. seealso::
   **Additional Resources:**

   - Grammar definition: ``pyfcstm/dsl/grammar/Grammar.g4``
   - Parser implementation: ``pyfcstm/dsl/parse.py``
   - Model system: ``pyfcstm/model/model.py``
   - Test suite: ``test/testfile/sample_codes/``

   For implementation details, refer to the grammar definition, parsing pipeline, and model system documentation. The test suite provides additional examples and validation patterns for complex use cases.

