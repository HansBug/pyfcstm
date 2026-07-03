.. _sec-reference-visualization-options:

Visualization options reference
===============================

``pyfcstm plantuml`` and ``pyfcstm visualize`` share PlantUML output options.
The CLI uses ``-l`` for detail presets and repeated ``-c key=value`` arguments
for typed option overrides.

Detail presets
--------------

.. list-table:: Detail presets
   :header-rows: 1

   * - Preset
     - Use
   * - ``minimal``
     - High-level structure with minimal details.
   * - ``normal``
     - Balanced view and the CLI default.
   * - ``full``
     - Detailed implementation view with more actions, events, guards, and effects.

CLI example:

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm -l full -o machine.full.puml

PlantUML options
----------------

The defaults below are constructor defaults. Options with default ``None`` are
resolved from ``detail_level`` presets or parent switches when PlantUML output is
rendered.

.. list-table:: PlantUML options
   :header-rows: 1

   * - Option
     - Values / type
     - Default
     - Meaning
   * - ``show_variable_definitions``
     - bool
     - ``None``
     - Show variable definitions; resolved by ``detail_level``.
   * - ``variable_display_mode``
     - ``note``, ``legend``, ``hide``
     - ``legend``
     - How variables are displayed.
   * - ``variable_legend_position``
     - position string
     - ``top left``
     - Legend position when variables use legend mode.
   * - ``state_name_format``
     - tuple of ``name``, ``extra_name``, ``path``
     - ``('extra_name',)``
     - State label components.
   * - ``show_pseudo_state_style``
     - bool
     - ``None``
     - Apply pseudo-state styling.
   * - ``collapse_empty_states``
     - bool
     - ``False``
     - Collapse states with no visible contents.
   * - ``show_lifecycle_actions``
     - bool
     - ``None``
     - Master lifecycle-action display switch.
   * - ``show_enter_actions`` / ``show_during_actions`` / ``show_exit_actions``
     - bool
     - ``None``
     - Individual lifecycle-action switches.
   * - ``show_aspect_actions``
     - bool
     - ``None``
     - Show ``>> during before/after`` aspect actions.
   * - ``show_abstract_actions``
     - bool
     - ``None``
     - Show abstract actions; inherits from ``show_lifecycle_actions``.
   * - ``show_concrete_actions``
     - bool
     - ``None``
     - Show concrete actions; inherits from ``show_lifecycle_actions``.
   * - ``abstract_action_marker``
     - ``text``, ``symbol``, ``none``
     - ``text``
     - How abstract actions are marked when displayed.
   * - ``max_action_lines``
     - int or ``None``
     - ``None``
     - Maximum visible lines per lifecycle action; ``None`` means unlimited.
   * - ``show_transition_guards``
     - bool
     - ``None``
     - Show transition guards.
   * - ``show_transition_effects``
     - bool
     - ``None``
     - Show transition effect blocks.
   * - ``transition_effect_mode``
     - ``note``, ``inline``, ``hide``
     - ``note``
     - How effects are displayed.
   * - ``show_events``
     - bool
     - ``None``
     - Show event names on transitions.
   * - ``event_name_format``
     - tuple of ``name``, ``extra_name``, ``path``, ``relpath``
     - ``('extra_name', 'relpath')``
     - Event label components.
   * - ``event_visualization_mode``
     - ``none``, ``color``, ``legend``, ``both``, ``dependency_view``
     - ``none``
     - Event visualization mode; ``dependency_view`` is reserved for dependency-view output.
   * - ``event_legend_position``
     - position string
     - ``right``
     - Event legend position.
   * - ``max_depth``
     - int or ``None``
     - ``None``
     - Maximum nested depth to expand.
   * - ``collapsed_state_marker``
     - str
     - ``...``
     - Marker for collapsed states.
   * - ``use_skinparam`` / ``use_stereotypes``
     - bool
     - ``True``
     - PlantUML styling switches.
   * - ``custom_colors``
     - dict or ``None``
     - ``None``
     - Python API only: custom event colors used by ``color`` and ``both`` event visualization modes.

CLI type syntax
---------------

* Boolean values accept forms such as ``true`` / ``false``.
* Tuple values use comma-separated components, for example
  ``-c state_name_format=name,path``.
* Use ``-l`` for ``detail_level``; do not pass it through ``-c``.
* Python-only object values such as ``custom_colors`` dictionaries require the
  Python API.

Examples
--------

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm \
     -c show_events=true \
     -c event_visualization_mode=both \
     -o machine.events.puml

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm \
     -c show_lifecycle_actions=true \
     -c show_exit_actions=false \
     -c max_depth=3 \
     -o machine.focused.puml
