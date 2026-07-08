.. _sec-reference-visualization-options:

Visualization options reference
===============================

``pyfcstm plantuml`` and ``pyfcstm visualize`` share the same PlantUML source
configuration. ``plantuml`` stops after writing PlantUML source. ``visualize``
uses the same source configuration, then renders an image or PDF through a
PlantUML backend. Use :doc:`/how_to/visualization/index` for task recipes and
this page for exact option facts.

The synchronization markers below are comments consumed by
``tools/check_visualization_reference_docs.py``. They cover every
``PlantUMLOptions`` field plus CLI renderer, type, environment, parser, and
failure-boundary facts.

.. visualization-ref-field: name=detail_level
.. visualization-ref-field: name=show_variable_definitions
.. visualization-ref-field: name=variable_display_mode
.. visualization-ref-field: name=variable_legend_position
.. visualization-ref-field: name=state_name_format
.. visualization-ref-field: name=show_pseudo_state_style
.. visualization-ref-field: name=collapse_empty_states
.. visualization-ref-field: name=show_lifecycle_actions
.. visualization-ref-field: name=show_enter_actions
.. visualization-ref-field: name=show_during_actions
.. visualization-ref-field: name=show_exit_actions
.. visualization-ref-field: name=show_aspect_actions
.. visualization-ref-field: name=show_abstract_actions
.. visualization-ref-field: name=show_concrete_actions
.. visualization-ref-field: name=abstract_action_marker
.. visualization-ref-field: name=max_action_lines
.. visualization-ref-field: name=show_transition_guards
.. visualization-ref-field: name=show_transition_effects
.. visualization-ref-field: name=transition_effect_mode
.. visualization-ref-field: name=show_events
.. visualization-ref-field: name=event_name_format
.. visualization-ref-field: name=event_visualization_mode
.. visualization-ref-field: name=event_legend_position
.. visualization-ref-field: name=max_depth
.. visualization-ref-field: name=collapsed_state_marker
.. visualization-ref-field: name=use_skinparam
.. visualization-ref-field: name=use_stereotypes
.. visualization-ref-field: name=custom_colors
.. visualization-ref-preset: name=minimal
.. visualization-ref-preset: name=normal
.. visualization-ref-preset: name=full
.. visualization-ref-renderer: name=local
.. visualization-ref-renderer: name=remote
.. visualization-ref-renderer: name=auto
.. visualization-ref-render-type: name=png
.. visualization-ref-render-type: name=svg
.. visualization-ref-render-type: name=pdf
.. visualization-ref-envvar: name=PLANTUML_JAR
.. visualization-ref-envvar: name=PLANTUML_HOST
.. visualization-ref-envvar: name=PYFCSTM_NO_GUI
.. visualization-ref-envvar: name=CI
.. visualization-ref-envvar: name=DISPLAY
.. visualization-ref-envvar: name=WAYLAND_DISPLAY
.. visualization-ref-envvar: name=MIR_SOCKET
.. visualization-ref-envvar: name=XDG_CACHE_HOME
.. visualization-ref-envvar: name=LOCALAPPDATA
.. visualization-ref-parser-form: group=value bool int float quoted-string none null tuple optional invalid-key invalid-value
.. visualization-ref-boundary: group=behavior renderer-auto-fallback suffix-mismatch check-mode headless-open strict-open remote-privacy cache-output local-backend-failure remote-network-failure backend-success-without-output source-only-plantuml rendered-image-visualize

Mental model
------------

Visualization has two independent layers:

1. **PlantUML source layer.** ``PlantUMLOptions`` decides which model facts are
   visible in the generated PlantUML text: variables, lifecycle actions,
   guards, effects, events, state labels, hierarchy depth, and styling.
2. **Rendered artifact layer.** ``visualize`` chooses a renderer backend, file
   type, output path, and viewer behavior. These settings do not change the
   model facts in the PlantUML source; they only decide how the source becomes
   ``png``, ``svg``, or ``pdf``.

Detail presets
--------------

The ``-l`` / ``--level`` CLI option maps to ``PlantUMLOptions.detail_level``.
Use it for the main audience choice, then add ``-c key=value`` overrides only
for specific deviations.

.. list-table:: Detail presets
   :header-rows: 1

   * - Preset
     - Resolved defaults
     - Best use
   * - ``minimal``
     - Shows variable definitions, transition guards, transition effects, and events. Hides lifecycle actions and pseudo-state styling.
     - Presentations and architecture views where state shape matters more than implementation detail.
   * - ``normal``
     - Shows variable definitions, transition guards, transition effects, events, and pseudo-state styling. Hides lifecycle actions.
     - General documentation, code review, and quick model understanding.
   * - ``full``
     - Shows variable definitions, lifecycle actions, transition guards, transition effects, events, and pseudo-state styling.
     - Deep debugging, semantic review, and generated-runtime alignment discussion.

Preset examples:

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm -l minimal -o machine.minimal.puml
   pyfcstm plantuml -i machine.fcstm -l normal -o machine.normal.puml
   pyfcstm plantuml -i machine.fcstm -l full -o machine.full.puml

PlantUML option fields
----------------------

Options with default ``None`` are resolved by ``PlantUMLOptions.to_config()``.
Resolution order is: explicit value, parent switch, detail preset, then final
fallback. Parent switches are especially important for lifecycle actions:
``show_enter_actions``, ``show_during_actions``, ``show_exit_actions``,
``show_aspect_actions``, ``show_abstract_actions``, and
``show_concrete_actions`` inherit from ``show_lifecycle_actions`` when they are
``None``.

.. list-table:: Complete ``PlantUMLOptions`` field map
   :header-rows: 1

   * - Field
     - CLI form
     - Default
     - Values
     - Effect and notes
   * - ``detail_level``
     - ``-l minimal|normal|full``
     - ``normal``
     - ``minimal``, ``normal``, ``full``
     - Main preset. Use ``-l`` on the CLI; do not pass ``-c detail_level=...`` because the command already passes the preset separately.
   * - ``show_variable_definitions``
     - ``-c show_variable_definitions=true``
     - ``None``
     - bool or ``None`` in Python
     - Show the ``def`` variable inventory. ``None`` resolves from the preset.
   * - ``variable_display_mode``
     - ``-c variable_display_mode=legend``
     - ``legend``
     - ``note``, ``legend``, ``hide``
     - Choose whether variables appear as a PlantUML note, a legend table, or not at all.
   * - ``variable_legend_position``
     - ``-c 'variable_legend_position=bottom right'``
     - ``top left``
     - ``top left``, ``top center``, ``top right``, ``bottom left``, ``bottom center``, ``bottom right``, ``left``, ``right``, ``center``
     - Position for variable legends. Quote the shell argument when the value contains a space.
   * - ``state_name_format``
     - ``-c state_name_format=extra_name,name``
     - ``('extra_name',)``
     - tuple of ``name``, ``extra_name``, ``path``
     - Components for state labels. The first visible component is primary; additional components appear in parentheses.
   * - ``show_pseudo_state_style``
     - ``-c show_pseudo_state_style=true``
     - ``None``
     - bool or ``None`` in Python
     - Apply pseudo-state visual styling. ``minimal`` resolves this to ``False``; ``normal`` and ``full`` resolve it to ``True``.
   * - ``collapse_empty_states``
     - ``-c collapse_empty_states=true``
     - ``False``
     - bool
     - Compact states with no visible action text.
   * - ``show_lifecycle_actions``
     - ``-c show_lifecycle_actions=true``
     - ``None``
     - bool or ``None`` in Python
     - Master switch for enter, during, exit, aspect, abstract, and concrete action visibility.
   * - ``show_enter_actions``
     - ``-c show_enter_actions=true``
     - ``None``
     - bool or ``None`` in Python
     - Show only enter actions when overriding the lifecycle parent switch.
   * - ``show_during_actions``
     - ``-c show_during_actions=true``
     - ``None``
     - bool or ``None`` in Python
     - Show during actions when visible lifecycle details are needed.
   * - ``show_exit_actions``
     - ``-c show_exit_actions=true``
     - ``None``
     - bool or ``None`` in Python
     - Show exit actions.
   * - ``show_aspect_actions``
     - ``-c show_aspect_actions=true``
     - ``None``
     - bool or ``None`` in Python
     - Show ``>> during before`` and ``>> during after`` aspect actions.
   * - ``show_abstract_actions``
     - ``-c show_abstract_actions=true``
     - ``None``
     - bool or ``None`` in Python
     - Show abstract lifecycle actions, often useful for integration surfaces.
   * - ``show_concrete_actions``
     - ``-c show_concrete_actions=true``
     - ``None``
     - bool or ``None`` in Python
     - Show concrete operation bodies, often useful for implementation review.
   * - ``abstract_action_marker``
     - ``-c abstract_action_marker=symbol``
     - ``text``
     - ``text``, ``symbol``, ``none``
     - Render abstract actions as text, a guillemet marker, or without an abstract marker.
   * - ``max_action_lines``
     - ``-c max_action_lines=3``
     - ``None``
     - integer or ``None`` in Python
     - Limit visible lines per action. Use this when full diagrams become too tall.
   * - ``show_transition_guards``
     - ``-c show_transition_guards=false``
     - ``None``
     - bool or ``None`` in Python
     - Show or hide transition guard conditions.
   * - ``show_transition_effects``
     - ``-c show_transition_effects=false``
     - ``None``
     - bool or ``None`` in Python
     - Show or hide transition effect blocks.
   * - ``transition_effect_mode``
     - ``-c transition_effect_mode=inline``
     - ``note``
     - ``note``, ``inline``, ``hide``
     - Choose note-on-link effects, compact inline effects, or hidden effects.
   * - ``show_events``
     - ``-c show_events=false``
     - ``None``
     - bool or ``None`` in Python
     - Show or hide event names on transitions.
   * - ``event_name_format``
     - ``-c event_name_format=extra_name,relpath``
     - ``('extra_name', 'relpath')``
     - tuple of ``name``, ``extra_name``, ``path``, ``relpath``
     - Components for event labels. ``path`` is absolute; ``relpath`` follows the transition's event reference when available.
   * - ``event_visualization_mode``
     - ``-c event_visualization_mode=both``
     - ``none``
     - ``none``, ``color``, ``legend``, ``both``, ``dependency_view``
     - Add event colors, an event legend, both, or no special event visualization. ``dependency_view`` is reserved and should not be used as a normal diagram mode.
   * - ``event_legend_position``
     - ``-c event_legend_position=right``
     - ``right``
     - same position labels as ``variable_legend_position``
     - Position for the event legend when event legend output is enabled.
   * - ``max_depth``
     - ``-c max_depth=2``
     - ``None``
     - integer or ``None`` in Python
     - Limit expanded hierarchy depth and insert a collapsed-state marker below the limit.
   * - ``collapsed_state_marker``
     - ``-c collapsed_state_marker='[more]'``
     - ``...``
     - string
     - Text shown for collapsed descendants when ``max_depth`` hides deeper states.
   * - ``use_skinparam``
     - ``-c use_skinparam=false``
     - ``True``
     - bool
     - Include or omit the pyfcstm PlantUML style block.
   * - ``use_stereotypes``
     - ``-c use_stereotypes=false``
     - ``True``
     - bool
     - Include or omit PlantUML stereotypes such as ``<<pseudo>>`` and ``<<composite>>``.
   * - ``custom_colors``
     - Python API only
     - ``None``
     - mapping or ``None``
     - Custom event color mapping for ``color`` and ``both`` event modes. The CLI does not parse dictionaries for this option.

Typed ``-c`` value syntax
-------------------------

The CLI accepts repeated ``-c key=value`` arguments and parses values with the
same helper used by other pyfcstm configuration paths.

.. list-table:: Value forms
   :header-rows: 1

   * - Form
     - Examples
     - Result
     - Notes
   * - bool
     - ``true``, ``yes``, ``1``, ``false``, ``no``, ``0``
     - Python ``bool``
     - For bool-typed fields, only these forms are accepted.
   * - int
     - ``3``, ``0``
     - Python ``int``
     - Used by ``max_depth`` and ``max_action_lines``.
   * - float
     - ``1.5``
     - Python ``float``
     - Auto parser supports floats, though current PlantUML CLI fields do not require float-specific options.
   * - quoted string
     - ``'variable_legend_position=bottom right'``
     - Python ``str``
     - Quote the entire shell argument when spaces are part of the value.
   * - none/null
     - ``none``, ``null``
     - Python ``None`` in auto mode or None-typed fields
     - Most CLI fields use explicit concrete types, so ``None`` is mainly a Python API pattern.
   * - tuple
     - ``state_name_format=extra_name,name``
     - tuple of strings
     - Used by ``state_name_format`` and ``event_name_format``.
   * - optional value
     - omitted option, or explicit ``None`` in Python
     - inherited/resolved value
     - Optional booleans resolve through parent switches and presets.
   * - invalid key
     - ``-c does_not_exist=true``
     - command failure
     - Unknown keys reach ``PlantUMLOptions`` construction and are rejected.
   * - invalid value
     - ``-c max_depth=abc``
     - command failure
     - Type-specific parsing reports the offending key.

CLI examples:

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm -c show_events=true -c max_depth=2
   pyfcstm plantuml -i machine.fcstm -c state_name_format=extra_name,name
   pyfcstm plantuml -i machine.fcstm -c 'variable_legend_position=bottom right'

Python API examples:

.. code-block:: python

   from pyfcstm.model.plantuml import PlantUMLOptions

   api_surface = PlantUMLOptions(
       detail_level='full',
       show_concrete_actions=False,
       show_abstract_actions=True,
       abstract_action_marker='symbol',
   )

   event_view = PlantUMLOptions(
       event_visualization_mode='both',
       custom_colors={'System.Start': '#00AA00'},
   )

Renderer and file options
-------------------------

These options belong to ``visualize`` only. They do not affect PlantUML source
content.

.. list-table:: Renderer and file facts
   :header-rows: 1

   * - Fact
     - Values
     - Meaning
   * - Renderer mode
     - ``local``, ``remote``, ``auto``
     - ``local`` uses Java plus a PlantUML jar; ``remote`` uses a PlantUML server; ``auto`` tries local then remote.
   * - Render type
     - ``png``, ``svg``, ``pdf``
     - Output file type. The output suffix must match the selected type when a suffix is provided.
   * - Cache path
     - platform-specific
     - Used when ``visualize -o`` is omitted. Linux honors ``XDG_CACHE_HOME``; Windows honors ``LOCALAPPDATA``.
   * - Check mode
     - ``pyfcstm visualize --check``
     - Checks renderer availability and exits without parsing a DSL file.
   * - Open mode
     - ``--open`` / ``--no-open`` / ``--strict-open``
     - Controls viewer launch after rendering. Headless environments skip viewer launch unless strict mode is requested.

Environment variables
---------------------

.. list-table:: Environment variables
   :header-rows: 1

   * - Variable
     - Used by
     - Meaning
   * - ``PLANTUML_JAR``
     - ``visualize --renderer local``
     - Default PlantUML jar path when ``-p`` / ``--plantuml-jar`` is omitted.
   * - ``PLANTUML_HOST``
     - ``visualize --renderer remote``
     - Default remote PlantUML server when ``-r`` / ``--remote-host`` is omitted.
   * - ``PYFCSTM_NO_GUI``
     - ``visualize --open``
     - Truthy value disables automatic viewer launch.
   * - ``CI``
     - ``visualize --open``
     - Truthy value marks the environment as headless.
   * - ``DISPLAY`` / ``WAYLAND_DISPLAY`` / ``MIR_SOCKET``
     - Linux viewer detection
     - At least one normally indicates a graphical session on Linux.
   * - ``XDG_CACHE_HOME``
     - Linux cache output
     - Base directory for omitted ``visualize -o`` outputs.
   * - ``LOCALAPPDATA``
     - Windows cache output
     - Base directory for omitted ``visualize -o`` outputs on Windows.

Behavior boundaries
-------------------

.. list-table:: Boundary facts
   :header-rows: 1

   * - Boundary
     - Exact behavior
   * - ``renderer-auto-fallback``
     - ``auto`` tries local rendering first and falls back to remote rendering only if local backend creation/check fails.
   * - ``suffix-mismatch``
     - ``visualize -o diagram.svg -t png`` fails before rendering because ``.svg`` does not match ``png``.
   * - ``check-mode``
     - ``--check`` does not require ``-i`` and does not parse any DSL file.
   * - ``headless-open``
     - In headless environments, normal ``--open`` prints a skip message and keeps a successful render successful.
   * - ``strict-open``
     - ``--strict-open`` turns viewer-launch failure or headless skip into a command failure.
   * - ``remote-privacy``
     - Remote rendering sends the generated PlantUML source to the configured service. Use local rendering for private diagrams.
   * - ``cache-output``
     - Omitted ``-o`` writes to the pyfcstm visualize cache instead of the current directory.
   * - ``local-backend-failure``
     - Local failures name the local renderer and include the underlying ``plantumlcli``/Java/path error class when available.
   * - ``remote-network-failure``
     - Remote failures name the remote renderer and include the underlying network/request error when available.
   * - ``backend-success-without-output``
     - If ``plantumlcli`` reports success but no file is created, pyfcstm treats it as a failure.
   * - ``source-only-plantuml``
     - ``plantuml`` never renders an image and never checks renderer availability.
   * - ``rendered-image-visualize``
     - ``visualize`` always goes through PlantUML source first, then renders the requested artifact type.
