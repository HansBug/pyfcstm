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

Common option groups
--------------------

.. list-table:: PlantUML option groups
   :header-rows: 1

   * - Option
     - Values / type
     - Meaning
   * - ``show_variable_definitions``
     - bool
     - Show variable definitions.
   * - ``variable_display_mode``
     - ``note``, ``legend``, ``hide``
     - How variables are displayed.
   * - ``variable_legend_position``
     - position string
     - Legend position when variables use legend mode.
   * - ``state_name_format``
     - tuple of ``name``, ``extra_name``, ``path``
     - State label components.
   * - ``show_pseudo_state_style``
     - bool
     - Apply pseudo-state styling.
   * - ``collapse_empty_states``
     - bool
     - Collapse states with no visible contents.
   * - ``show_lifecycle_actions``
     - bool
     - Master lifecycle-action display switch.
   * - ``show_enter_actions`` / ``show_during_actions`` / ``show_exit_actions``
     - bool
     - Individual lifecycle-action switches.
   * - ``show_aspect_actions``
     - bool
     - Show ``>> during before/after`` aspect actions.
   * - ``show_transition_guards``
     - bool
     - Show transition guards.
   * - ``show_transition_effects``
     - bool
     - Show transition effect blocks.
   * - ``transition_effect_mode``
     - ``note``, ``inline``, ``hide``
     - How effects are displayed.
   * - ``show_events``
     - bool
     - Show event names on transitions.
   * - ``event_name_format``
     - tuple of ``name``, ``extra_name``, ``path``, ``relpath``
     - Event label components.
   * - ``event_visualization_mode``
     - ``none``, ``color``, ``legend``, ``both``, ``dependency_view``
     - Event visualization mode; ``dependency_view`` is reserved for dependency-view output.
   * - ``event_legend_position``
     - position string
     - Event legend position.
   * - ``max_depth``
     - int
     - Maximum nested depth to expand.
   * - ``collapsed_state_marker``
     - str
     - Marker for collapsed states.
   * - ``use_skinparam`` / ``use_stereotypes``
     - bool
     - PlantUML styling switches.

CLI type syntax
---------------

* Boolean values accept forms such as ``true`` / ``false``.
* Tuple values use comma-separated components, for example
  ``-c state_name_format=name,path``.
* Use ``-l`` for ``detail_level``; do not pass it through ``-c``.
* Python-only object values such as custom color dictionaries require the
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
