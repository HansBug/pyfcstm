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

.. visualization-ref-field: name=detail_level default=normal
.. visualization-ref-field: name=show_variable_definitions default=None
.. visualization-ref-field: name=variable_display_mode default=legend
.. visualization-ref-field: name=variable_legend_position default="top left"
.. visualization-ref-field: name=state_name_format default=extra_name
.. visualization-ref-field: name=show_pseudo_state_style default=None
.. visualization-ref-field: name=collapse_empty_states default=False
.. visualization-ref-field: name=show_lifecycle_actions default=None
.. visualization-ref-field: name=show_enter_actions default=None
.. visualization-ref-field: name=show_during_actions default=None
.. visualization-ref-field: name=show_exit_actions default=None
.. visualization-ref-field: name=show_aspect_actions default=None
.. visualization-ref-field: name=show_abstract_actions default=None
.. visualization-ref-field: name=show_concrete_actions default=None
.. visualization-ref-field: name=abstract_action_marker default=text
.. visualization-ref-field: name=max_action_lines default=None
.. visualization-ref-field: name=show_transition_guards default=None
.. visualization-ref-field: name=show_transition_effects default=None
.. visualization-ref-field: name=transition_effect_mode default=note
.. visualization-ref-field: name=show_events default=None
.. visualization-ref-field: name=event_name_format default=extra_name,relpath
.. visualization-ref-field: name=event_visualization_mode default=none
.. visualization-ref-field: name=event_legend_position default=right
.. visualization-ref-field: name=max_depth default=None
.. visualization-ref-field: name=collapsed_state_marker default=...
.. visualization-ref-field: name=use_skinparam default=True
.. visualization-ref-field: name=use_stereotypes default=True
.. visualization-ref-field: name=custom_colors default=None
.. visualization-ref-preset: name=minimal defaults=show_variable_definitions=True,show_pseudo_state_style=False,show_lifecycle_actions=False,show_enter_actions=False,show_during_actions=False,show_exit_actions=False,show_aspect_actions=False,show_abstract_actions=False,show_concrete_actions=False,show_transition_guards=True,show_transition_effects=True,show_events=True
.. visualization-ref-preset: name=normal defaults=show_variable_definitions=True,show_pseudo_state_style=True,show_lifecycle_actions=False,show_enter_actions=False,show_during_actions=False,show_exit_actions=False,show_aspect_actions=False,show_abstract_actions=False,show_concrete_actions=False,show_transition_guards=True,show_transition_effects=True,show_events=True
.. visualization-ref-preset: name=full defaults=show_variable_definitions=True,show_pseudo_state_style=True,show_lifecycle_actions=True,show_enter_actions=True,show_during_actions=True,show_exit_actions=True,show_aspect_actions=True,show_abstract_actions=True,show_concrete_actions=True,show_transition_guards=True,show_transition_effects=True,show_events=True
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

Reference-grade option scenarios
--------------------------------

The reference tables below are exhaustive by field, but field rows alone do not
show how options combine. These scenarios pin the most common combinations to
observable outcomes and failure boundaries.

.. list-table:: Option scenarios and boundaries
   :header-rows: 1

   * - Scenario
     - Example
     - Expected effect
     - Boundary or counterexample
   * - Preset-only source export.
     - ``pyfcstm plantuml -i docs/source/tutorials/visualization/example.fcstm -l minimal -o /tmp/minimal.puml``
     - Uses the ``minimal`` preset for source text and writes no image.
     - Passing ``-t svg`` to ``plantuml`` is invalid because render type belongs to ``visualize``.
   * - Preset plus narrow override.
     - ``pyfcstm plantuml -i docs/source/tutorials/visualization/example.fcstm -l full -c max_action_lines=3 -o /tmp/compact.puml``
     - Keeps full visibility while limiting each action block to three visible lines.
     - Prefer ``-l full`` for the preset; ``-c detail_level=full`` is also valid, and an explicit ``-l`` wins with a warning when the values conflict.
   * - Event-oriented diagram.
     - ``pyfcstm plantuml -i docs/source/tutorials/visualization/example.fcstm -c event_visualization_mode=both -o /tmp/events.puml``
     - Shows events directly in transitions and in event-supporting visual structures.
     - Invalid enum values fail during option parsing before a renderer is called.
   * - Headless render.
     - ``pyfcstm visualize -i docs/source/tutorials/visualization/example.fcstm -t svg -o /tmp/example.svg --no-open``
     - Writes an SVG and skips desktop viewer launch.
     - Without ``--no-open``, GUI availability can affect the final open step even after rendering succeeds.
   * - Local renderer privacy.
     - ``pyfcstm visualize -i docs/source/tutorials/visualization/example.fcstm --renderer local -p ./plantuml.jar --no-open``
     - Keeps PlantUML source on the local machine when Java and the jar are available.
     - Missing jar or Java is a local backend failure, not a model or PlantUML-option failure.
   * - Remote renderer convenience.
     - ``pyfcstm visualize -i docs/source/tutorials/visualization/example.fcstm --renderer remote --no-open``
     - Sends PlantUML source to the configured remote host and writes the rendered artifact.
     - Do not use for private diagrams unless sending the source to that host is acceptable.

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
     - Main preset. It may also be supplied through ``-c detail_level=...``. If an explicit ``-l/--level`` and ``-c`` value disagree, the CLI emits a warning and the explicit ``-l/--level`` value wins.
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

Field and renderer example cards
--------------------------------

The table above gives the closed field list. The cards below show how groups of fields interact in real commands. They are intentionally repetitive: each row gives a concrete command, the expected source or rendering signal, and the reason to choose or avoid it.

Preset resolution examples
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: Examples
   :header-rows: 1

   * - Use case
     - Command
     - Expected effect
     - Selection rule
   * - Minimal structure review
     - ``pyfcstm plantuml -i machine.fcstm -l minimal -o machine.min.puml``
     - Shows hierarchy, variables, transition guards/effects, and events; hides lifecycle action text and pseudo-state styling.
     - Use for architecture discussion where implementation bodies would distract.
   * - Normal documentation view
     - ``pyfcstm plantuml -i machine.fcstm -l normal -o machine.normal.puml``
     - Adds pseudo-state styling while keeping lifecycle actions hidden.
     - Use for most documentation and review snippets.
   * - Full semantic review
     - ``pyfcstm plantuml -i machine.fcstm -l full -o machine.full.puml``
     - Shows lifecycle action families and concrete/abstract action visibility controlled by the detail preset.
     - Use for semantic review, generated-runtime alignment, or debugging.
   * - Override after preset
     - ``pyfcstm plantuml -i machine.fcstm -l minimal -c show_lifecycle_actions=true -o machine.min-actions.puml``
     - Explicit value wins over preset defaults.
     - Use sparingly when a mostly minimal diagram needs one semantic dimension.

Review note:
  If the command changes source visibility, verify the generated ``.puml``. If it changes rendering behavior, verify ``visualize --check`` or the rendered artifact path.

Variable and state label examples
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: Examples
   :header-rows: 1

   * - Use case
     - Command
     - Expected effect
     - Selection rule
   * - Legend variables
     - ``pyfcstm plantuml -i machine.fcstm -c variable_display_mode=legend -o machine.vars.puml``
     - Variable definitions render in a PlantUML legend.
     - Good when variables are global context for the whole diagram.
   * - Hide variables
     - ``pyfcstm plantuml -i machine.fcstm -c variable_display_mode=hide -o machine.no-vars.puml``
     - Variable inventory is removed from the source.
     - Good for structure-only diagrams.
   * - Dual state labels
     - ``pyfcstm plantuml -i machine.fcstm -c state_name_format=extra_name,name -o machine.labels.puml``
     - State labels include both readable extra name and raw model name.
     - Good when generated identifiers and DSL names both matter.
   * - Collapsed depth
     - ``pyfcstm plantuml -i machine.fcstm -c max_depth=2 -c collapsed_state_marker="[more]" -o machine.depth.puml``
     - Descendants beyond depth are replaced by the marker.
     - Good for large hierarchical models.

Review note:
  If the command changes source visibility, verify the generated ``.puml``. If it changes rendering behavior, verify ``visualize --check`` or the rendered artifact path.

Lifecycle visibility examples
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: Examples
   :header-rows: 1

   * - Use case
     - Command
     - Expected effect
     - Selection rule
   * - Master lifecycle switch
     - ``pyfcstm plantuml -i machine.fcstm -c show_lifecycle_actions=true -o machine.lifecycle.puml``
     - Enter, during, exit, aspect, abstract, and concrete action families inherit visible defaults.
     - Use when lifecycle ordering is part of review.
   * - Only abstract hooks
     - ``pyfcstm plantuml -i machine.fcstm -c show_lifecycle_actions=false -c show_abstract_actions=true -o machine.hooks.puml``
     - Abstract extension points remain visible while concrete bodies stay hidden.
     - Use for integration-surface reviews.
   * - Limit action text
     - ``pyfcstm plantuml -i machine.fcstm -l full -c max_action_lines=3 -o machine.short-actions.puml``
     - Long action bodies are clipped after the configured line count.
     - Use when full diagrams become too tall.
   * - Aspect-only review
     - ``pyfcstm plantuml -i machine.fcstm -c show_lifecycle_actions=false -c show_aspect_actions=true -o machine.aspects.puml``
     - Descendant-cycle before/after aspects are visible without other lifecycle bodies.
     - Use when reviewing cross-cutting behavior.

Review note:
  If the command changes source visibility, verify the generated ``.puml``. If it changes rendering behavior, verify ``visualize --check`` or the rendered artifact path.

Transition and event examples
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: Examples
   :header-rows: 1

   * - Use case
     - Command
     - Expected effect
     - Selection rule
   * - Hide guards
     - ``pyfcstm plantuml -i machine.fcstm -c show_transition_guards=false -o machine.no-guards.puml``
     - Transition labels omit guard conditions.
     - Use only when guards are not relevant to the audience.
   * - Inline effects
     - ``pyfcstm plantuml -i machine.fcstm -c transition_effect_mode=inline -o machine.inline-effects.puml``
     - Transition effects appear compactly on the transition instead of note blocks.
     - Use for small effect bodies.
   * - Event legend
     - ``pyfcstm plantuml -i machine.fcstm -c event_visualization_mode=legend -o machine.event-legend.puml``
     - Events get a legend without coloring transitions.
     - Use when event names repeat often.
   * - Event colors and legend
     - ``pyfcstm plantuml -i machine.fcstm -c event_visualization_mode=both -o machine.event-colors.puml``
     - Events are colored and listed in the legend.
     - Use for event-flow diagrams.

Review note:
  If the command changes source visibility, verify the generated ``.puml``. If it changes rendering behavior, verify ``visualize --check`` or the rendered artifact path.

Renderer and environment examples
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: Examples
   :header-rows: 1

   * - Use case
     - Command
     - Expected effect
     - Selection rule
   * - Source-only export
     - ``pyfcstm plantuml -i machine.fcstm -o machine.puml``
     - No renderer is checked or used.
     - Safe even when Java or network rendering is unavailable.
   * - Backend check
     - ``pyfcstm visualize --check --renderer auto``
     - Reports local and remote availability and exits without parsing DSL.
     - Use before CI rendering jobs.
   * - Cache output
     - ``pyfcstm visualize -i machine.fcstm --no-open``
     - Writes to the pyfcstm visualize cache when -o is omitted.
     - Use only for local preview, not reproducible build outputs.
   * - Strict open
     - ``pyfcstm visualize -i machine.fcstm --strict-open``
     - Viewer launch failure becomes command failure.
     - Use only for desktop workflows that require opening the image.

Review note:
  If the command changes source visibility, verify the generated ``.puml``. If it changes rendering behavior, verify ``visualize --check`` or the rendered artifact path.

Invalid value examples
~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: Examples
   :header-rows: 1

   * - Use case
     - Command
     - Expected effect
     - Selection rule
   * - Unknown field
     - ``pyfcstm plantuml -i machine.fcstm -c does_not_exist=true``
     - Fails because the key is not a PlantUMLOptions field.
     - Check the complete field table.
   * - Wrong integer
     - ``pyfcstm plantuml -i machine.fcstm -c max_depth=abc``
     - Fails because max_depth expects an integer or None.
     - Use a number such as 2.
   * - Wrong render type suffix
     - ``pyfcstm visualize -i machine.fcstm -o machine.svg -t png --no-open``
     - Fails before rendering because suffix and type disagree.
     - Use -o machine.png or -t svg.
   * - Private source over remote
     - ``pyfcstm visualize -i private.fcstm --renderer remote --no-open``
     - This may succeed but sends PlantUML source to a service.
     - Use local rendering for private diagrams.

Review note:
  If the command changes source visibility, verify the generated ``.puml``. If it changes rendering behavior, verify ``visualize --check`` or the rendered artifact path.

Resolution trace: lifecycle actions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Lifecycle visibility is the most common place where users misread the option model. The resolved value is not simply the dataclass default:

1. An explicit child switch such as ``show_enter_actions=false`` wins first.
2. If the child switch is ``None``, it inherits from ``show_lifecycle_actions`` when that parent switch is explicit.
3. If the parent switch is also ``None``, the selected detail preset supplies the default.
4. Final fallback values are applied only after those steps.

.. list-table:: Lifecycle resolution examples
   :header-rows: 1

   * - Input
     - Resolved meaning
     - Reader-visible result
   * - ``-l minimal``
     - lifecycle parent and child switches resolve false.
     - lifecycle text is hidden.
   * - ``-l full``
     - lifecycle parent and child switches resolve true.
     - enter/during/exit/aspect/abstract/concrete actions are visible unless another option hides them.
   * - ``-l full -c show_concrete_actions=false``
     - concrete body visibility is explicitly false; other full preset action groups remain visible.
     - abstract hooks can remain visible while implementation bodies are hidden.
   * - ``-c show_lifecycle_actions=false -c show_enter_actions=true``
     - explicit child switch overrides explicit parent switch for enter actions.
     - enter actions are visible even though other lifecycle groups remain hidden.



Per-field scenario matrix
-------------------------

The complete field map above is intentionally closed-list. The matrix below is
more practical: every public field gets two normal examples and one boundary
example. Use it when a review needs to prove that a diagram choice is deliberate
rather than accidental.

.. list-table:: Source visibility and label fields
   :header-rows: 1

   * - Field
     - Example A
     - Example B
     - Boundary or counterexample
   * - ``detail_level``
     - ``-l minimal`` for a small hierarchy review.
     - ``-l full`` when lifecycle actions are the topic.
     - ``-l normal -c detail_level=full`` emits a conflict warning and uses ``normal`` because ``normal`` was explicitly written through ``-l``. Omitting ``-l`` leaves the Click default and does not create a second assignment.
   * - ``show_variable_definitions``
     - ``-c show_variable_definitions=true`` to prove variable declarations in a review.
     - ``-c show_variable_definitions=false`` for a structure-only diagram.
     - ``variable_display_mode=hide`` also hides variables even when this switch is true.
   * - ``variable_display_mode``
     - ``legend`` keeps variables compact for documentation pages.
     - ``note`` makes variables stand out near the state graph.
     - ``hide`` is not a position; it suppresses variable output.
   * - ``variable_legend_position``
     - ``top left`` leaves right-side event legends free.
     - ``bottom right`` works when the top of the diagram is dense.
     - Quote values containing spaces in shells.
   * - ``state_name_format``
     - ``extra_name`` shows the display label when available.
     - ``extra_name,name`` keeps both human label and DSL identifier.
     - ``path`` can make large diagrams noisy; reserve it for ambiguity removal.
   * - ``show_pseudo_state_style``
     - ``true`` makes pseudo states visually distinct in normal/full diagrams.
     - ``false`` keeps minimal diagrams less stylized.
     - It affects styling only, not whether pseudo states exist in the model.
   * - ``collapse_empty_states``
     - ``true`` shortens states with no visible action text.
     - ``false`` keeps normal PlantUML state blocks for readability.
     - If lifecycle details are hidden, a state may become visually empty even though it has hidden actions.
   * - ``max_depth``
     - ``1`` keeps only root-level structure for a high-level review.
     - ``2`` shows one nested layer while hiding deeper details.
     - It hides diagram detail only; it does not delete model states.
   * - ``collapsed_state_marker``
     - ``...`` is compact and neutral.
     - ``[hidden children]`` is explicit for documentation readers.
     - The marker appears only when ``max_depth`` actually collapses descendants.

.. list-table:: Lifecycle and action fields
   :header-rows: 1

   * - Field
     - Example A
     - Example B
     - Boundary or counterexample
   * - ``show_lifecycle_actions``
     - ``true`` when entry/during/exit order is the review target.
     - ``false`` when transitions and hierarchy matter more than action bodies.
     - Child switches override it only when they are explicitly set.
   * - ``show_enter_actions``
     - ``true`` with ``show_lifecycle_actions=false`` to spotlight initialization hooks.
     - ``false`` with ``show_lifecycle_actions=true`` to hide noisy entry details.
     - ``None`` in Python means inherit, not false.
   * - ``show_during_actions``
     - ``true`` for cycle-behavior reviews.
     - ``false`` when only transitions should be emphasized.
     - Aspect ``during`` hooks are governed separately by ``show_aspect_actions``.
   * - ``show_exit_actions``
     - ``true`` when cleanup behavior is important.
     - ``false`` for compact state inventories.
     - Hiding exit actions does not hide transition effects.
   * - ``show_aspect_actions``
     - ``true`` to show ``>> during before`` and ``>> during after`` hooks.
     - ``false`` when leaf-local actions are enough for the reader.
     - It is about aspect hooks, not ordinary transition guards.
   * - ``show_abstract_actions``
     - ``true`` when generated-code integration hooks must be visible.
     - ``false`` when only concrete operations are being audited.
     - It filters action visibility after lifecycle visibility has allowed the action group.
   * - ``show_concrete_actions``
     - ``true`` to audit assignments and operation bodies.
     - ``false`` to show only abstract extension points.
     - It does not change generated runtime behavior.
   * - ``abstract_action_marker``
     - ``text`` preserves the DSL word ``abstract``.
     - ``symbol`` uses a compact ``«abstract»`` marker.
     - ``none`` can hide the distinction; use it only when the caption explains the choice.
   * - ``max_action_lines``
     - ``3`` keeps long actions readable in a normal diagram.
     - ``1`` shows only the first line as a locator.
     - ``0`` or ``None`` does not provide a useful line cap in the same way as a positive integer.

.. list-table:: Transition, event, and styling fields
   :header-rows: 1

   * - Field
     - Example A
     - Example B
     - Boundary or counterexample
   * - ``show_transition_guards``
     - ``true`` for reachability and condition review.
     - ``false`` for a pure topology diagram.
     - Hiding guards can make mutually exclusive paths look ambiguous.
   * - ``show_transition_effects``
     - ``true`` when variable updates matter.
     - ``false`` for compact routing diagrams.
     - Effects may still exist in the model even if hidden from the diagram.
   * - ``transition_effect_mode``
     - ``note`` keeps long effects off the edge label.
     - ``inline`` is compact for short assignments.
     - ``hide`` suppresses effect text even when effects are present.
   * - ``show_events``
     - ``true`` to explain event-triggered transitions.
     - ``false`` for diagrams focused only on possible movement.
     - Event colors and legends are not useful if events are hidden.
   * - ``event_name_format``
     - ``extra_name,relpath`` is compact and user-facing.
     - ``name,path`` is useful when absolute ownership matters.
     - ``relpath`` depends on the transition's event reference when available.
   * - ``event_visualization_mode``
     - ``color`` colors event families without adding a legend.
     - ``both`` uses colors plus legend for documentation.
     - ``dependency_view`` is reserved and should not be treated as the normal event mode.
   * - ``event_legend_position``
     - ``right`` keeps event explanations beside the graph.
     - ``bottom center`` works for wide diagrams.
     - It matters only when event legend output is enabled.
   * - ``use_skinparam``
     - ``true`` applies pyfcstm's default PlantUML styling.
     - ``false`` lets a downstream PlantUML theme own styling.
     - Turning it off can make pseudo/composite distinctions less visible.
   * - ``use_stereotypes``
     - ``true`` emits stereotypes such as ``<<pseudo>>``.
     - ``false`` produces plainer PlantUML source.
     - Some style rules depend on stereotypes, so disabling them can change visual meaning.
   * - ``custom_colors``
     - Python API code can map event groups to stable colors.
     - Use it for a publication diagram that must match a legend palette.
     - The CLI cannot parse dictionary values for this field.

.. list-table:: Renderer and environment decision fields
   :header-rows: 1

   * - Decision
     - Example A
     - Example B
     - Boundary or counterexample
   * - Render type
     - ``-t svg`` for scalable documentation.
     - ``-t png`` for screenshots or quick previews.
     - The output suffix must match the type when a suffix is provided.
   * - Renderer mode
     - ``--renderer local`` for private diagrams.
     - ``--renderer remote`` when an approved service owns rendering.
     - ``--renderer auto`` may fall back to remote after local failure.
   * - Local backend paths
     - ``-j /usr/bin/java`` fixes the Java executable.
     - ``-p ./plantuml.jar`` fixes the PlantUML jar.
     - These options do not affect remote rendering.
   * - Remote backend host
     - ``-r http://www.plantuml.com/plantuml`` uses the public default explicitly.
     - ``PLANTUML_HOST=https://plantuml.internal/plantuml`` uses an internal service.
     - Remote rendering sends source text to that host.
   * - Viewer behavior
     - ``--no-open`` is the stable scripted form.
     - ``--strict-open`` is appropriate only when opening the viewer is itself required.
     - CI, ``PYFCSTM_NO_GUI``, and missing display variables can skip ordinary ``--open``.

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
     - Unknown keys are rejected at the CLI boundary with the supported-key list and, when close, a spelling suggestion.
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

Python Diagram API and browser viewer
--------------------------------------

The browser viewer is a separate public path from the PlantUML options above.
It consumes the parsed model directly and writes portable JSON or a
self-contained HTML file.

.. list-table:: Python Diagram public values
   :header-rows: 1

   * - Value
     - Accepted values or default
     - Behavior
   * - ``DiagramOptions.detail_level``
     - ``minimal``, ``normal`` (default), ``full``
     - Selects the renderer's detail preset, and each draws a different diagram.
       ``minimal`` writes transition effects inline and leaves edges in the
       neutral stroke, listing events in the legend only; ``normal``, the
       default, puts effects in a note beside the transition and tints edges by
       event; ``full`` adds a leaf state's own events and lifecycle actions as
       rows under its title, while a composite state shows its children instead
       and gains no rows at any level. The details panel lists a state's actions
       whatever the preset, so the level chooses what the drawing carries rather
       than what is available to read.
   * - ``DiagramOptions.direction``
     - ``TB`` (default) or ``LR``
     - Chooses top-to-bottom or left-to-right layout.
   * - ``DiagramOptions.palette``
     - ``default``, ``nord``, ``solarized``, ``darcula``, or ``None``
     - Selects the viewer palette.
   * - ``DiagramOptions.mode``
     - ``light``, ``dark``, ``auto``, or ``None``
     - Selects the initial color mode.
   * - ``DiagramOptions.cjk_locale``
     - ``sc``, ``tc``, ``hk``, ``jp``, or ``kr`` (default ``sc``)
     - Embeds the matching CJK font pair in the HTML file.
   * - ``DiagramViewState.mode``
     - ``compare`` (default), ``fcstm``, or ``diagram``
     - Selects the source-only, diagram-only, or linked split view.
   * - ``DiagramViewState.zoom``
     - Finite positive number or ``None`` (default ``None``)
     - Sets the initial diagram zoom; boolean, zero, negative, NaN, and infinity values fail.
       ``None`` leaves the framing to the viewer, which fits the whole diagram to the viewport.
   * - ``DiagramViewState.pan_x`` / ``pan_y``
     - Finite numbers or ``None`` (default ``None``)
     - Sets the initial diagram translation. ``None`` defers to the fitted framing; when any one
       of ``zoom`` / ``pan_x`` / ``pan_y`` is set, the remaining ``None`` fields fall back to
       ``1.0`` and ``0.0`` so an explicit request is honoured exactly.

``model.diagram(...)`` returns an immutable ``Diagram`` snapshot. Its
``to_dict()`` and ``to_json()`` results omit absolute paths, source ranges, and
editor selection state. ``to_html()`` returns one complete HTML string;
``save("name.json")`` and ``save("name.html")`` use atomic replacement: an
interrupted save leaves the file that was already there, with its content and
permissions intact. A file being replaced keeps the permissions it had, and a new
one gets what your umask gives any other new file in that directory — so a umask
that clears the write bit produces a read-only result which ``save()`` can still
replace, because it is yours. A file belonging to another user that you cannot
write is refused instead, and on Windows so is one marked read-only. The
HTML path is also returned by ``Diagram.show()`` and ``StateMachine.show()``.
With a window and no explicit path, ``show()`` blocks until the window is closed
and then removes the document it wrote, so the returned path no longer exists —
pass an explicit path for a viewer you want to keep. Without a window and without
a path, nothing removes it. Either way the file is written 0600 inside a directory
of your own that no other local user may look into, because a viewer carries the
model's source: a name derived from the document, and the exact size of a ~29 MB
document, each identify which diagram it is to anyone able to list them. Asking
again for the same diagram returns the same file rather than another copy. That
reuse follows the directory rather than the process: another process of yours that
resolves the same one is handed the same path, and a forked child inherits it — so
the file is shared for removal too, and a peer's cleanup of what it was handed
removes yours. Where that directory turns out to belong to somebody else or to be
open to them, each resolution makes its own instead and says so in a warning, which
two independent processes do separately and a forked child does not. Pass an
explicit path for a document only you may remove. On Windows this rests on
``%TEMP%`` being per account, which is the default; a ``TEMP`` shared between
users is not detectable, and with an installer from python.org the directory's mode
is applied only from 3.12.4 onwards — pass a path of your own for a document that
must not be somewhere shared.

The HTML viewer can download SVG, PNG, and vector PDF in a browser. The Python
methods ``to_svg()``, ``to_png()``, and ``to_pdf()`` intentionally raise
``DiagramUnavailableError`` until the later headless delivery stage. Calling
``show()`` without a Chromium-family browser raises the same typed capability
error after the HTML file has been written; ``show(open_window=False)`` avoids
the browser requirement.

The HTML viewer needs nothing beyond a browser. ``DiagramAssetEngine``'s
headless rendering does need the optional MiniRacer runtime, which
``pip install pyfcstm[viz]`` provides; without it the engine raises
``DiagramUnavailableError`` naming that command. Installing the extra does not
enable ``to_svg()`` / ``to_png()`` / ``to_pdf()`` — those wait for the headless
delivery stage regardless.

Unknown option fields, duplicate snake/camel aliases, invalid enum values, and
invalid numeric values raise ``ValueError``; a ``collapsed_state_ids`` that is
not a sequence of ID strings raises ``TypeError``, including the common mistake
of passing one ID as a bare string.

``with_options`` and ``with_view_state`` treat their keyword form as a partial
update: fields that are not named keep their current value. Passing a value
positionally replaces the whole object instead. Missing or unusable packaged
viewer/WASM/font assets raise ``DiagramAssetError`` with development recovery
guidance (``make build_assets``) or the project issue URL for installed packages.

Synchronous export and its size limits
--------------------------------------

``to_svg()``, ``to_png(scale=...)`` and ``to_pdf()`` export without a browser.
They need the optional rendering runtime that ``pip install pyfcstm[viz]``
provides; without it each raises ``DiagramUnavailableError`` naming that extra.
``save()`` routes a ``.svg``, ``.png`` or ``.pdf`` suffix to them, and the CLI
accepts the same three suffixes plus ``--scale``.

.. list-table:: Synchronous export surface
   :header-rows: 1

   * - Call
     - Returns
     - Notes
   * - ``Diagram.to_svg()``
     - ``str``
     - The expanded form: glyphs and arrow heads are already paths, so the
       document carries no ``<text>``, ``<marker>`` or font dependency and renders
       identically where none of this project's fonts are installed. The
       renderer's raw canonical SVG is an internal intermediate and is not what
       this returns.
   * - ``Diagram.to_png(scale=1.0)``
     - ``bytes``
     - Rasterised through the pinned resvg backend, opaque, at ``ceil(size *
       scale)`` pixels.
   * - ``Diagram.to_pdf()``
     - ``bytes``
     - One page sized to the diagram, drawn as vectors with no image object.
       Text is outlines, so the document is **not searchable** -- that is the cost
       of it rendering without this project's fonts.
   * - ``Diagram._repr_svg_()``
     - ``str`` or ``None``
     - Notebook representation, the same expanded SVG. Returns ``None`` when the
       optional runtime is absent, because an exception raised from a repr hook
       replaces the whole cell output with a traceback.

.. note::
   The viewer's own PNG download rasterises at a fixed 2x, while
   ``to_png()`` defaults to 1x.  Comparing a downloaded file with an
   API-produced one therefore shows a factor-of-two difference in pixels that is
   two different requests rather than a disagreement; pass ``scale=2`` to compare
   like with like.

Every export is bounded. The limits are checked in Python before the rasteriser
or the PDF writer is reached, so an impossible request is named rather than
discovered by exhausting memory.

.. list-table:: Export size limits
   :header-rows: 1

   * - Limit
     - Value
     - Raised on breach
   * - ``scale``
     - ``0 < scale <= 4``
     - ``ValueError``
   * - Scaled width and height, each
     - ``<= 16384`` px
     - ``DiagramRenderLimitError``
   * - Scaled pixel count
     - ``<= 16777216``
     - ``DiagramRenderLimitError``
   * - Raw RGBA buffer
     - ``<= 67108864`` bytes, which is the pixel cap times four
     - Reported as the pixel limit
   * - Encoded PNG
     - ``<= 33554432`` bytes
     - ``DiagramRenderLimitError``
   * - Encoded SVG or PDF
     - ``<= 67108864`` bytes
     - ``DiagramRenderLimitError``

``DiagramRenderLimitError`` carries a ``limit_name``, and the only values it takes
are ``edge``, ``pixels``, ``png``, ``pdf`` and ``svg``.  There is no ``raw_rgba``: the raw
buffer is four bytes per pixel and its bound is the pixel bound times four, so any
request large enough to reach it has already been refused as a pixel-count
breach.  The figure is listed above because the documented limit set names a
buffer size, not because it is a separate boundary.

The encoded-size limits are enforced on the Python export path, where the bytes
are produced.  The browser download enforces the scale, edge and pixel limits; it
does not weigh its own output.

``DiagramRenderLimitError`` is a sibling of ``DiagramRenderError``, not a
subclass. The two describe different situations with different remedies: a render
failure means the renderer was asked to do something and could not, while a limit
failure means it was never asked. Lowering ``scale`` fixes the latter and nothing
else, so ``except DiagramRenderError`` must not absorb it.

The message names the original size, the scaled size, the limit that fired and
what to change, because "too large" alone does not tell a caller which scale would
have fitted.

The browser download enforces the same product limits and refuses past them.
Separately, it clamps at the limits a browser canvas actually has
(``RASTER_MAX_SIDE``, ``RASTER_MAX_AREA``), which are not product policy: a tall
diagram at 2x once produced a null blob and took the SVG and PDF download down
with it. Every product limit is stricter than the host limit it shadows, so the
refusal always fires first and the clamp is a defensive second layer ordinary
input never reaches.

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

Outlining a drawing you already have
------------------------------------

``Diagram.to_svg()`` covers the case where you hold a model.  ``pyfcstm
expand-svg`` covers the opposite one: you hold a canonical SVG -- rendered
somewhere else, with a palette and colour mode already chosen -- and want its
text turned into paths.

.. code-block:: shell-session

    $ pyfcstm expand-svg -i canonical.svg -o self-contained.svg
    self-contained.svg
    $ pyfcstm expand-svg -i canonical.svg > self-contained.svg

The document handed in is the document expanded.  Re-rendering from the
``.fcstm`` source instead would return a valid file in the *default* palette,
discarding whatever presentation choices produced the input -- a wrong-colour
export that every structural check accepts.  The CJK face is read from the
input's own ``font-family``, so there is no locale flag.

.. list-table::
    :header-rows: 1
    :widths: 30 70

    * - Condition
      - Result
    * - The optional runtime is missing
      - Names the extra to install; nothing is written.
    * - The input is not an SVG document
      - A usage error, before the renderer starts.
    * - The result exceeds ``MAX_EXPORT_TEXT_BYTES``
      - :class:`~pyfcstm.diagram.engine.DiagramRenderLimitError` with
        ``limit_name`` ``svg``, the same ceiling ``to_svg()`` enforces.

The editor preview is the caller this was added for.  A webview has the diagram
on screen but no fonts and no rasteriser, and bundling those would add 17.7 MB
to the extension for one CJK locale or 59.4 MB for all of them.  It therefore
asks an installed ``pyfcstm[viz]``: set ``fcstm.diagram.pyfcstmPath`` to name a
specific interpreter, or leave it empty to try ``pyfcstm``, then ``python3 -m
pyfcstm``, then ``python -m pyfcstm``.  With nothing usable installed the export
says so, rather than handing over a document whose text depends on fonts the
reader may not have.

Why these boundaries exist
--------------------------

This page states the facts; :doc:`/explanations/visualization/index` explains the
reasoning behind the viewer ones -- the self-contained document, the blocking window,
the directory-level privacy boundary, and the reclaim at exit.
