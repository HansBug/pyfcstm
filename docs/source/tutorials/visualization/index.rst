FCSTM Visualization Guide
===============================================

This guide provides a comprehensive introduction to visualizing finite state machines defined in the FCSTM DSL. You'll learn how to generate PlantUML diagrams using both Python code and the command-line interface, and how to customize the visualization output using the flexible configuration system.

Overview
---------------------------------------

pyfcstm provides two primary methods for visualizing state machines:

1. **Python API**: Programmatic control with the ``PlantUMLOptions`` class
2. **Command-Line Interface**: Quick visualization with flexible configuration options

Both methods support the same comprehensive configuration system, allowing you to control every aspect of the generated PlantUML diagrams.

Example State Machine
---------------------------------------

Throughout this guide, we'll use the following example state machine to demonstrate all visualization features:

.. literalinclude:: example.fcstm
   :language: fcstm
   :caption: example.fcstm

This state machine demonstrates key FCSTM features:

- **Variables**: ``counter`` and ``error_count`` for state tracking
- **Hierarchical states**: ``Active`` contains nested ``Processing`` and ``Waiting`` states
- **Lifecycle actions**: ``enter`` and ``during`` actions for state behavior
- **Aspect actions**: ``>> during before`` applies to all descendant states
- **Abstract actions**: ``GlobalMonitor`` must be implemented in generated code
- **Transitions with guards**: ``Active -> Error : if [counter > 100]``
- **Transitions with effects**: ``Active -> Idle :: Stop effect { counter = 0; }``
- **Forced transitions**: ``!* -> Error :: FatalError`` from all states

**Visualization**

Here's what this state machine looks like when visualized with default settings:

.. figure:: example.fcstm.puml.svg
   :alt: Example state machine visualization
   :align: center
   :width: 100%

   Default visualization of the example state machine

Visualization Methods
---------------------------------------

Python API Visualization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Python API provides programmatic control over visualization through the ``PlantUMLOptions`` class.

**Basic Usage**

.. literalinclude:: python_basic.demo.py
   :language: python
   :caption: Basic Python visualization

Output:

.. literalinclude:: python_basic.demo.py.txt
   :language: text

**Generated Visualization**

.. figure:: output_basic.puml.svg
   :alt: Basic Python visualization output
   :align: center
   :width: 80%

   PlantUML diagram generated with default settings

**With Custom Options**

.. literalinclude:: python_options.demo.py
   :language: python
   :caption: Python visualization with PlantUMLOptions

Output:

.. literalinclude:: python_options.demo.py.txt
   :language: text

**Generated Visualization**

.. figure:: output_custom.puml.svg
   :alt: Python visualization with custom options
   :align: center
   :width: 80%

   PlantUML diagram with custom PlantUMLOptions (full detail level, events enabled, max depth 3)

CLI Visualization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The command-line interface provides quick access to visualization with flexible configuration.

**Basic Usage**

.. literalinclude:: cli_basic.demo.sh
   :language: bash
   :caption: Basic CLI visualization

Output:

.. literalinclude:: cli_basic.demo.sh.txt
   :language: text

**Generated Visualization**

.. figure:: output_cli_basic.puml.svg
   :alt: CLI basic visualization output
   :align: center
   :width: 80%

   PlantUML diagram generated with CLI default settings

Configuration System
---------------------------------------

The visualization system provides comprehensive configuration through ``PlantUMLOptions``. All options are available in both Python API and CLI.

Configuration Options Reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following table provides a complete reference of all available configuration options:

.. list-table:: PlantUMLOptions Configuration Reference
   :widths: 25 15 15 45
   :header-rows: 1

   * - Option
     - Type
     - Default
     - Description
   * - **Preset Level**
     -
     -
     -
   * - ``detail_level``
     - str
     - ``'normal'``
     - Preset detail level: ``'minimal'``, ``'normal'``, or ``'full'``
   * - **Variable Display**
     -
     -
     -
   * - ``show_variable_definitions``
     - bool
     - ``None``
     - Show variable definitions (inherits from detail_level if None, defaults to True for all levels)
   * - ``variable_display_mode``
     - str
     - ``'legend'``
     - How to display variables: ``'note'``, ``'legend'``, or ``'hide'``
   * - ``variable_legend_position``
     - str
     - ``'top left'``
     - Legend position: ``'top left'``, ``'top center'``, ``'top right'``, ``'bottom left'``, ``'bottom center'``, ``'bottom right'``, ``'left'``, ``'right'``, ``'center'``
   * - **State Formatting**
     -
     -
     -
   * - ``state_name_format``
     - tuple
     - ``('extra_name',)``
     - State name format: ``'name'``, ``'extra_name'``, ``'path'``
   * - ``show_pseudo_state_style``
     - bool
     - ``None``
     - Apply dotted border styling to pseudo states
   * - ``collapse_empty_states``
     - bool
     - ``False``
     - Hide action text for states with no lifecycle actions
   * - **Lifecycle Actions**
     -
     -
     -
   * - ``show_lifecycle_actions``
     - bool
     - ``None``
     - Master switch for all lifecycle actions (enter/during/exit/aspect)
   * - ``show_enter_actions``
     - bool
     - ``None``
     - Show enter actions (inherits from show_lifecycle_actions)
   * - ``show_during_actions``
     - bool
     - ``None``
     - Show during actions (inherits from show_lifecycle_actions)
   * - ``show_exit_actions``
     - bool
     - ``None``
     - Show exit actions (inherits from show_lifecycle_actions)
   * - ``show_aspect_actions``
     - bool
     - ``None``
     - Show aspect actions (``>> during before/after``)
   * - **Action Details**
     -
     -
     -
   * - ``show_abstract_actions``
     - bool
     - ``None``
     - Show abstract actions (inherits from show_lifecycle_actions)
   * - ``show_concrete_actions``
     - bool
     - ``None``
     - Show concrete actions (inherits from show_lifecycle_actions)
   * - ``abstract_action_marker``
     - str
     - ``'text'``
     - Abstract action marker: ``'text'``, ``'symbol'``, or ``'none'``
   * - ``max_action_lines``
     - int
     - ``None``
     - Maximum lines per action (None = unlimited)
   * - **Transitions**
     -
     -
     -
   * - ``show_transition_guards``
     - bool
     - ``None``
     - Show guard conditions on transitions
   * - ``show_transition_effects``
     - bool
     - ``None``
     - Show transition effects
   * - ``transition_effect_mode``
     - str
     - ``'note'``
     - Effect display mode: ``'note'``, ``'inline'``, or ``'hide'``
   * - **Events**
     -
     -
     -
   * - ``show_events``
     - bool
     - ``None``
     - Show event names on transitions
   * - ``event_name_format``
     - tuple
     - ``('extra_name', 'relpath')``
     - Event name format: ``'name'``, ``'extra_name'``, ``'path'``, ``'relpath'``
   * - ``event_visualization_mode``
     - str
     - ``'none'``
     - Event visualization: ``'none'``, ``'color'``, ``'legend'``, ``'both'``
   * - ``event_legend_position``
     - str
     - ``'right'``
     - Event legend position: ``'top left'``, ``'top center'``, ``'top right'``, ``'bottom left'``, ``'bottom center'``, ``'bottom right'``, ``'left'``, ``'right'``, ``'center'``
   * - **Hierarchy Control**
     -
     -
     -
   * - ``max_depth``
     - int
     - ``None``
     - Maximum nesting depth to visualize (None = unlimited)
   * - ``collapsed_state_marker``
     - str
     - ``'...'``
     - Text marker for collapsed states
   * - **PlantUML Styling**
     -
     -
     -
   * - ``use_skinparam``
     - bool
     - ``True``
     - Include skinparam styling block
   * - ``use_stereotypes``
     - bool
     - ``True``
     - Add stereotype markers (``<<pseudo>>``, ``<<composite>>``)
   * - ``custom_colors``
     - dict
     - ``None``
     - Custom color mapping for events (event path -> hex color)

**Notes:**

- Options with ``None`` default inherit from ``detail_level`` preset or parent options
- ``show_lifecycle_actions`` controls defaults for enter/during/exit/aspect/abstract/concrete actions
- Tuple options accept multiple format elements combined in display order
- CLI uses ``-c key=value`` syntax for configuration

Detail Level Presets
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Detail level presets provide quick configuration for common use cases:

- **minimal**: Bare structure with minimal details
- **normal**: Balanced view with essential information (default)
- **full**: Complete details including all actions and events

**Python API**

.. literalinclude:: python_detail_levels.demo.py
   :language: python
   :caption: Detail levels in Python

Output:

.. literalinclude:: python_detail_levels.demo.py.txt
   :language: text

**Visual Comparison**

The three detail levels produce significantly different visualization outputs:

**Minimal Detail Level**

.. figure:: output_python_minimal.puml.svg
   :alt: Minimal detail level visualization
   :align: center
   :width: 70%

   Minimal: Basic state structure only, no actions or detailed information

**Normal Detail Level** (Default)

.. figure:: output_python_normal.puml.svg
   :alt: Normal detail level visualization
   :align: center
   :width: 70%

   Normal: Balanced view with essential lifecycle actions and transition information

**Full Detail Level**

.. figure:: output_python_full.puml.svg
   :alt: Full detail level visualization
   :align: center
   :width: 70%

   Full: Complete details including all actions, events, guards, and effects

**CLI**

.. literalinclude:: cli_level.demo.sh
   :language: bash
   :caption: Detail levels in CLI

Output:

.. literalinclude:: cli_level.demo.sh.txt
   :language: text

**Visual Comparison of Detail Levels**

The three detail levels produce significantly different visualization outputs. Here's a side-by-side comparison:

.. list-table:: Detail Level Comparison
   :widths: 33 33 33
   :header-rows: 1

   * - Minimal
     - Normal (Default)
     - Full
   * - Basic structure only
     - Essential information
     - Complete details
   * - No lifecycle actions
     - Key actions shown
     - All actions visible
   * - Minimal transitions
     - Important transitions
     - All transitions with guards/effects

The generated PlantUML files demonstrate these differences:

- **Minimal**: ``output_minimal.puml`` - Bare state structure
- **Normal**: ``output_normal.puml`` - Balanced view with essential details
- **Full**: ``output_full.puml`` - Complete visualization with all information

Variable Display Options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Control how state machine variables are displayed in the diagram.

**Configuration Options**

- ``show_variable_definitions`` (bool): Show variable definitions at the top (defaults to True for all detail levels)
- ``variable_display_mode`` (str): Display mode - ``'note'``, ``'legend'``, or ``'hide'`` (default: ``'legend'``)
- ``variable_legend_position`` (str): Legend position when using ``'legend'`` mode (default: ``'top left'``)

  - Available positions: ``'top left'``, ``'top center'``, ``'top right'``, ``'bottom left'``, ``'bottom center'``, ``'bottom right'``, ``'left'``, ``'right'``, ``'center'``

**Example**

.. code-block:: python

   from pyfcstm.model.plantuml import PlantUMLOptions

   # Show variables as a legend at top-left (default)
   options = PlantUMLOptions(
       show_variable_definitions=True,
       variable_display_mode='legend',
       variable_legend_position='top left'
   )

   # Place legend at bottom-right
   options = PlantUMLOptions(
       show_variable_definitions=True,
       variable_display_mode='legend',
       variable_legend_position='bottom right'
   )

**CLI Equivalent**

.. code-block:: bash

   # Default position (top left)
   pyfcstm plantuml -i example.fcstm \
     -c show_variable_definitions=true \
     -c variable_display_mode=legend \
     -o output.puml

   # Custom position
   pyfcstm plantuml -i example.fcstm \
     -c show_variable_definitions=true \
     -c variable_display_mode=legend \
     -c variable_legend_position="bottom right" \
     -o output.puml

State Name Formatting
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Customize how state names are displayed in the diagram.

**Configuration Options**

- ``state_name_format`` (tuple[str, ...]): Format components - ``'name'``, ``'path'``, ``'relpath'``
- ``show_pseudo_state_style`` (bool): Apply special styling to pseudo states
- ``collapse_empty_states`` (bool): Collapse states with no actions or substates

**Example**

.. code-block:: python

   # Show both name and full path
   options = PlantUMLOptions(
       state_name_format=('name', 'path'),
       show_pseudo_state_style=True,
       collapse_empty_states=False
   )

**CLI Equivalent**

.. code-block:: bash

   pyfcstm plantuml -i example.fcstm \
     -c state_name_format=name,path \
     -c show_pseudo_state_style=true \
     -c collapse_empty_states=false \
     -o output.puml

Lifecycle Actions Display
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Control which lifecycle actions (enter, during, exit) are shown in the diagram.

**Configuration Options**

- ``show_lifecycle_actions`` (bool): Master switch for all lifecycle actions
- ``show_enter_actions`` (bool): Show enter actions
- ``show_during_actions`` (bool): Show during actions
- ``show_exit_actions`` (bool): Show exit actions
- ``show_aspect_actions`` (bool): Show aspect actions (``>> during before/after``)
- ``show_abstract_actions`` (bool): Show abstract action declarations
- ``show_concrete_actions`` (bool): Show concrete action implementations
- ``abstract_action_marker`` (str): Marker for abstract actions (default: ``'«abstract»'``)
- ``max_action_lines`` (int): Maximum lines to show per action block

**Example**

.. code-block:: python

   # Show only enter and during actions, hide exit actions
   options = PlantUMLOptions(
       show_lifecycle_actions=True,
       show_enter_actions=True,
       show_during_actions=True,
       show_exit_actions=False,
       show_abstract_actions=True,
       max_action_lines=10
   )

**CLI Equivalent**

.. literalinclude:: cli_config.demo.sh
   :language: bash
   :caption: Lifecycle actions configuration

Output:

.. literalinclude:: cli_config.demo.sh.txt
   :language: text

**Generated Visualizations**

The lifecycle actions configuration produces different outputs based on which actions are shown:

.. figure:: output_lifecycle.puml.svg
   :alt: Lifecycle actions configuration visualization
   :align: center
   :width: 80%

   Custom lifecycle actions display (enter and during shown, exit hidden)

Transition Display Options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Control how transitions are displayed in the diagram.

**Configuration Options**

- ``show_transition_guards`` (bool): Show guard conditions on transitions
- ``show_transition_effects`` (bool): Show effect blocks on transitions
- ``transition_effect_mode`` (str): How to display effects - ``'note'`` or ``'inline'``

**Example**

.. code-block:: python

   # Show guards and effects as notes
   options = PlantUMLOptions(
       show_transition_guards=True,
       show_transition_effects=True,
       transition_effect_mode='note'
   )

**CLI Equivalent**

.. code-block:: bash

   pyfcstm plantuml -i example.fcstm \
     -c show_transition_guards=true \
     -c show_transition_effects=true \
     -c transition_effect_mode=note \
     -o output.puml

Event Visualization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Control how events are displayed in the diagram.

**Configuration Options**

- ``show_events`` (bool): Show event names on transitions
- ``event_name_format`` (tuple[str, ...]): Format components - ``'name'``, ``'path'``, ``'relpath'``
- ``event_visualization_mode`` (str): Visualization mode - ``'none'``, ``'color'``, ``'legend'``, or ``'both'``
- ``event_legend_position`` (str): Event legend position when using ``'legend'`` or ``'both'`` mode (default: ``'right'``)

  - Available positions: ``'top left'``, ``'top center'``, ``'top right'``, ``'bottom left'``, ``'bottom center'``, ``'bottom right'``, ``'left'``, ``'right'``, ``'center'``

**Example**

.. code-block:: python

   # Show events with color coding
   options = PlantUMLOptions(
       show_events=True,
       event_name_format=('name', 'relpath'),
       event_visualization_mode='color'
   )

   # Show event legend at custom position
   options = PlantUMLOptions(
       event_visualization_mode='legend',
       event_legend_position='bottom right'
   )

   # Show both colors and legend with custom positions
   options = PlantUMLOptions(
       event_visualization_mode='both',
       event_legend_position='top right'
   )

**CLI Equivalent**

.. code-block:: bash

   # Color mode
   pyfcstm plantuml -i example.fcstm \
     -c show_events=true \
     -c event_name_format=name,relpath \
     -c event_visualization_mode=color \
     -o output.puml

   # Legend mode with custom position
   pyfcstm plantuml -i example.fcstm \
     -c event_visualization_mode=legend \
     -c event_legend_position="bottom right" \
     -o output.puml

Depth Control
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Control how deep the visualization goes into nested states.

**Configuration Options**

- ``max_depth`` (int): Maximum nesting depth to visualize (0 = unlimited)
- ``collapsed_state_marker`` (str): Marker for collapsed states (default: ``'...'``)

**Example**

.. code-block:: python

   # Limit to 2 levels of nesting
   options = PlantUMLOptions(
       max_depth=2,
       collapsed_state_marker='[collapsed]'
   )

**CLI Equivalent**

.. code-block:: bash

   pyfcstm plantuml -i example.fcstm \
     -c max_depth=2 \
     -c collapsed_state_marker=[collapsed] \
     -o output.puml

PlantUML Styling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Control PlantUML-specific styling features.

**Configuration Options**

- ``use_skinparam`` (bool): Use skinparam for styling (default: True)
- ``use_stereotypes`` (bool): Use stereotypes for state classification (default: True)

**Example**

.. code-block:: python

   # Disable skinparam and stereotypes
   options = PlantUMLOptions(
       use_skinparam=False,
       use_stereotypes=False
   )

**CLI Equivalent**

.. code-block:: bash

   pyfcstm plantuml -i example.fcstm \
     -c use_skinparam=false \
     -c use_stereotypes=false \
     -o output.puml

Advanced Configuration
---------------------------------------

Combining Multiple Options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can combine multiple configuration options to create highly customized visualizations.

**Python API**

.. code-block:: python

   from pyfcstm.model.plantuml import PlantUMLOptions

   # Create a comprehensive custom configuration
   options = PlantUMLOptions(
       detail_level='full',
       show_events=True,
       event_visualization_mode='both',
       show_lifecycle_actions=True,
       show_enter_actions=True,
       show_during_actions=True,
       show_exit_actions=True,
       show_abstract_actions=True,
       max_action_lines=10,
       state_name_format=('name', 'path'),
       event_name_format=('name', 'relpath'),
       max_depth=3,
       use_stereotypes=True,
       use_skinparam=True
   )

   plantuml_output = model.to_plantuml(options)

**CLI**

.. literalinclude:: cli_advanced.demo.sh
   :language: bash
   :caption: Advanced CLI configuration

Output:

.. literalinclude:: cli_advanced.demo.sh.txt
   :language: text

**Generated Visualization**

.. figure:: output_advanced.puml.svg
   :alt: Advanced configuration visualization
   :align: center
   :width: 90%

   Comprehensive custom configuration combining multiple options (full detail, events with color mode, all lifecycle actions, custom name formats, max depth 3)

Configuration Type System
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The CLI configuration system supports automatic type inference and explicit type hints:

**Supported Types**

- ``bool``: ``true``/``false``, ``yes``/``no``, ``1``/``0``
- ``int``: Integer values (e.g., ``42``, ``0xFF``, ``0b1010``)
- ``float``: Floating-point values (e.g., ``3.14``, ``2.5``)
- ``str``: String values (quoted or unquoted)
- ``tuple[T, ...]``: Variable-length tuples (e.g., ``name,path``)
- ``tuple[T1, T2]``: Fixed-length tuples with specific types

**Type Inference**

When no type hint is provided, the CLI automatically infers the type:

.. code-block:: bash

   # Inferred as int
   pyfcstm plantuml -i example.fcstm -c max_depth=3

   # Inferred as bool
   pyfcstm plantuml -i example.fcstm -c show_events=true

   # Inferred as tuple[str, ...]
   pyfcstm plantuml -i example.fcstm -c state_name_format=name,path

Best Practices
---------------------------------------

Choosing Detail Levels
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **minimal**: Use for high-level architecture overviews or when presenting to non-technical stakeholders
- **normal**: Use for general documentation and code reviews
- **full**: Use for detailed implementation documentation or debugging

Optimizing Diagram Readability
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Start with defaults**: Begin with default settings and adjust as needed
2. **Use depth limits**: For complex state machines, use ``max_depth`` to focus on specific levels
3. **Hide unnecessary details**: Disable actions or events that aren't relevant to your use case
4. **Use event visualization**: Enable ``event_visualization_mode='color'`` for better event tracking
5. **Collapse empty states**: Enable ``collapse_empty_states`` to reduce visual clutter

Performance Considerations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Large state machines may generate very large PlantUML files
- Use ``max_depth`` to limit complexity for initial exploration
- Consider generating multiple diagrams at different detail levels for different audiences

Next Steps
---------------------------------------

- Explore the :doc:`../cli/index` for more CLI features
- Learn about :doc:`../dsl/index` to create your own state machines
- Check out :doc:`../render/index` for code generation from state machines

Summary
---------------------------------------

This guide covered:

- Two visualization methods: Python API and CLI
- Comprehensive configuration system with ``PlantUMLOptions``
- Detail level presets (minimal, normal, full)
- Fine-grained control over variables, states, actions, transitions, and events
- Advanced configuration techniques and best practices

The flexible configuration system allows you to create visualizations tailored to your specific needs, from high-level overviews to detailed implementation diagrams.
