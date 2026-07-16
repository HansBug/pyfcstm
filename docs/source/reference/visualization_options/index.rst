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
