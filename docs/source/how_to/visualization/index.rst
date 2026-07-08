.. _sec-how-to-visualization:

Visualization tasks
===================

Use this guide when you need diagram source or rendered diagram files. For the
complete option table, see :doc:`/reference/visualization_options/index`. For a
first diagram walkthrough, see :doc:`/tutorials/visualization/index`.

Concrete input and visual evidence
----------------------------------

The concrete examples below use
``docs/source/tutorials/visualization/example.fcstm``. The visualization
tutorial already generates ``output_minimal.puml.svg``, ``output_normal.puml.svg``,
and ``output_full.puml.svg`` from that source, so this how-to can point to real
rendered artifacts instead of asking readers to trust option names.

Before comparing rendered images, export PlantUML source:

.. code-block:: bash

   pyfcstm plantuml -i docs/source/tutorials/visualization/example.fcstm -o /tmp/example.puml

Success means ``/tmp/example.puml`` exists, starts with ``@startuml``, and
contains the expected state names. If source export fails, fix DSL/model errors
before changing renderer settings. Rendering options cannot repair invalid
PlantUML source.

Choose source or rendered output
--------------------------------

.. list-table:: Output choice
   :header-rows: 1

   * - Need
     - Use
     - Why
   * - Reviewable diagram source
     - ``pyfcstm plantuml``
     - Produces deterministic ``.puml`` text and needs no renderer.
   * - Image or PDF artifact
     - ``pyfcstm visualize``
     - Builds the same PlantUML source and renders ``png``, ``svg``, or ``pdf``.
   * - CI without GUI
     - ``visualize --no-open``
     - Avoids desktop viewer dependence.
   * - Private diagrams
     - ``visualize --renderer local``
     - Avoids sending PlantUML source to a remote service.

Visualization task acceptance cards
-----------------------------------

Use these cards when deciding whether a diagram step is ready for a tutorial,
review note, or CI job.

.. list-table:: Visualization task evidence
   :header-rows: 1

   * - Task
     - Command
     - Success signal
     - Side effect
     - First troubleshooting step
   * - Review diagram source.
     - ``pyfcstm plantuml -i docs/source/tutorials/visualization/example.fcstm -o /tmp/example.puml``
     - ``/tmp/example.puml`` starts with ``@startuml`` and is diffable text.
     - Writes only the requested source file.
     - Run ``inspect`` on the same input if PlantUML export fails.
   * - Compare detail presets.
     - ``pyfcstm plantuml -i docs/source/tutorials/visualization/example.fcstm -l full -o /tmp/example.full.puml``
     - The full source includes lifecycle/action details that the minimal preset hides.
     - Writes a second source file for review.
     - Check :doc:`/reference/visualization_options/index` before mixing preset and ``-c`` overrides.
   * - Check renderer availability.
     - ``pyfcstm visualize --check --renderer auto``
     - Reports either a usable local/remote backend or a concrete backend error.
     - No diagram file is written.
     - Decide whether privacy requires ``--renderer local`` before accepting remote fallback.
   * - Render without GUI dependence.
     - ``pyfcstm visualize -i docs/source/tutorials/visualization/example.fcstm -t svg -o /tmp/example.svg --no-open``
     - ``/tmp/example.svg`` exists and is visually readable in the docs/review context.
     - Writes the rendered file and may populate renderer cache.
     - If the file is missing but the backend reported success, treat that as a renderer failure, not a DSL failure.
   * - Verify a documented figure.
     - Build HTML after regenerating the source diagram.
     - The figure is legible at the documented width and its caption states the claim it proves.
     - Updates generated image files when diagram sources changed.
     - Inspect the rendered HTML; source reST alone does not prove visual quality.

Export PlantUML source
----------------------

PlantUML source is the safest first artifact because it is text, deterministic,
and easy to diff:

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm -o machine.puml

Use a detail preset before adding individual overrides:

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm -l full -o machine.full.puml

Add repeated ``-c key=value`` only for a specific reading goal:

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm \
     -c show_events=true \
     -c max_depth=2 \
     -o machine.events-depth2.puml

Compare detail preset outputs
-----------------------------

The same model can be shown with different detail levels for different readers.
The examples below reuse generated artifacts from the visualization tutorial.

.. list-table:: Detail preset comparison
   :header-rows: 1

   * - Preset
     - Intended reader
     - What is hidden first
     - Existing source
   * - ``minimal``
     - Architecture discussion and non-implementation readers.
     - Lifecycle actions and pseudo-state styling.
     - :download:`output_minimal.puml <../../tutorials/visualization/output_minimal.puml>`
   * - ``normal``
     - General documentation and code review.
     - Lifecycle action bodies.
     - :download:`output_normal.puml <../../tutorials/visualization/output_normal.puml>`
   * - ``full``
     - Debugging, semantic review, and implementation discussion.
     - Nothing from the preset-level switches.
     - :download:`output_full.puml <../../tutorials/visualization/output_full.puml>`

.. figure:: ../../tutorials/visualization/output_minimal.puml.svg
   :alt: Minimal detail preset output
   :align: center
   :width: 70%

   ``minimal`` keeps the shape readable when the audience only needs structure.

.. figure:: ../../tutorials/visualization/output_normal.puml.svg
   :alt: Normal detail preset output
   :align: center
   :width: 70%

   ``normal`` is the default compromise for documentation and review.

.. figure:: ../../tutorials/visualization/output_full.puml.svg
   :alt: Full detail preset output
   :align: center
   :width: 70%

   ``full`` is useful when action and transition details are part of the review.

Focus a large model
-------------------

For large machines, reduce the question before adding visual detail. Good
focused diagrams usually answer one of these questions:

* What is the state hierarchy?
* Which events move the model?
* Which guards and effects control a transition family?
* Which lifecycle hooks are integration points?
* Which subtree should be discussed in this review?

Useful command patterns:

.. code-block:: bash

   # Limit hierarchy depth.
   pyfcstm plantuml -i machine.fcstm -c max_depth=2 -o machine.depth2.puml

   # Hide event names when structure is the main topic.
   pyfcstm plantuml -i machine.fcstm -c show_events=false -o machine.structure.puml

   # Show event grouping when event flow is the topic.
   pyfcstm plantuml -i machine.fcstm \
     -c event_visualization_mode=both \
     -o machine.events.puml

   # Show only a compact implementation view.
   pyfcstm plantuml -i machine.fcstm \
     -l full \
     -c max_action_lines=3 \
     -c transition_effect_mode=inline \
     -o machine.compact-full.puml

Render a final file directly
----------------------------

Use ``visualize`` after deciding that the environment should own rendering:

.. code-block:: bash

   pyfcstm visualize -i machine.fcstm -t svg -o machine.svg --no-open

Check renderer availability without reading a DSL file:

.. code-block:: bash

   pyfcstm visualize --check --renderer auto

Choose a renderer mode deliberately:

.. list-table:: Renderer choice
   :header-rows: 1

   * - Mode
     - Command shape
     - Use when
   * - ``auto``
     - ``pyfcstm visualize --check --renderer auto``
     - Local development where either local or remote rendering is acceptable.
   * - ``local``
     - ``pyfcstm visualize -i machine.fcstm --renderer local -p ./plantuml.jar --no-open``
     - Diagrams are private or builds must avoid network dependence.
   * - ``remote``
     - ``pyfcstm visualize -i machine.fcstm --renderer remote --no-open``
     - A configured PlantUML service is allowed and easier than local Java setup.

Keep CI diagram jobs stable
---------------------------

A CI diagram job should not depend on a desktop viewer:

.. code-block:: bash

   pyfcstm plantuml -i machines/main.fcstm -o build/main.puml
   pyfcstm visualize -i machines/main.fcstm -t svg -o build/main.svg --no-open

If rendering is optional in CI, split source export from rendered export. Source
export proves pyfcstm can parse and emit PlantUML; rendered export additionally
proves the renderer backend works.

Use Python API when CLI values are not enough
---------------------------------------------

The CLI supports scalar and tuple values. Use the Python API for object-valued
configuration such as event color dictionaries:

.. code-block:: python

   from pyfcstm.model.plantuml import PlantUMLOptions

   options = PlantUMLOptions(
       event_visualization_mode='color',
       custom_colors={'System.Start': '#00AA00'},
   )
   plantuml_text = model.to_plantuml(options)

For complete runnable examples, download
:download:`python_basic.demo.py <../../tutorials/visualization/python_basic.demo.py>`
and
:download:`python_options.demo.py <../../tutorials/visualization/python_options.demo.py>`.

Concrete visualization recipes
------------------------------

Each recipe below names the reader goal first. Start with source export when
reviewability matters, then render only when an image artifact is required.

.. list-table:: Focused visualization recipes
   :header-rows: 1

   * - Reader goal
     - Command
     - Expected artifact
     - Boundary
   * - Review hierarchy only.
     - ``pyfcstm plantuml -i machine.fcstm -l minimal -o machine.structure.puml``
     - Compact ``.puml`` source with implementation details hidden.
     - Does not check any renderer.
   * - Review state/event flow.
     - ``pyfcstm plantuml -i machine.fcstm -c event_visualization_mode=both -o machine.events.puml``
     - Source contains event-oriented labels/legend/color facts.
     - Event coloring can make large diagrams visually dense.
   * - Review lifecycle hooks.
     - ``pyfcstm plantuml -i machine.fcstm -l full -c show_concrete_actions=false -o machine.hooks.puml``
     - Abstract hooks remain visible while concrete bodies are hidden.
     - Good for integration discussions, not for operation-body audits.
   * - Review a large subtree.
     - ``pyfcstm plantuml -i machine.fcstm -c max_depth=2 -o machine.depth2.puml``
     - Deep descendants are collapsed after depth 2.
     - Hidden descendants still exist in the model.
   * - Produce an image in CI.
     - ``pyfcstm visualize -i machine.fcstm -t svg -o build/machine.svg --no-open``
     - SVG file appears at the requested path.
     - Requires a configured local or remote renderer.
   * - Check renderer before rendering.
     - ``pyfcstm visualize --check --renderer auto``
     - Backend availability report.
     - Does not parse the DSL and does not prove diagram content.

Visual review checklist
~~~~~~~~~~~~~~~~~~~~~~~

Before accepting a new or changed diagram in documentation, inspect the rendered
HTML and ask these questions:

* Are labels readable at the configured width?
* Does the caption state what the figure proves?
* Is the diagram source traceable to ``.fcstm`` or ``.puml`` input?
* Is a dense ``full`` view really needed, or would ``normal`` plus one override be clearer?
* If remote rendering was used, is it acceptable that PlantUML source left the local machine?



Worked task cards
-----------------

The recipes above are short command choices. The cards below expand each common
task into the full how-to contract: starting input, command, expected signal,
side effect, and first repair step. Keep new visualization tasks at this level
of specificity instead of adding bare command lists.

.. list-table:: Task cards
   :header-rows: 1

   * - Task
     - Start from
     - Command
     - Expected signal and side effect
     - First repair if it fails
   * - Review the hierarchy only
     - ``docs/source/tutorials/quick_start/traffic_light.fcstm`` or another small source file.
     - ``pyfcstm plantuml -i traffic_light.fcstm -l minimal -o traffic_light.minimal.puml``.
     - Text file starts with ``@startuml`` and contains a compact state hierarchy; no renderer is required.
     - If the command fails before writing, run ``pyfcstm inspect -i traffic_light.fcstm`` to locate parse/model errors.
   * - Explain events and guards
     - A model whose transitions use events or guards.
     - ``pyfcstm plantuml -i machine.fcstm -l normal -c show_events=true -c show_transition_guards=true -o machine.events.puml``.
     - Source labels should show the event names and guard conditions used by the transition family.
     - If labels are missing, confirm the transition syntax actually contains events/guards and that no override hides them.
   * - Show integration hooks
     - A model with abstract lifecycle actions.
     - ``pyfcstm plantuml -i machine.fcstm -l full -c show_concrete_actions=false -o machine.hooks.puml``.
     - The source emphasizes abstract hooks while suppressing implementation bodies.
     - If the diagram is still too dense, add ``-c max_action_lines=2`` or split by ``max_depth``.
   * - Produce a CI SVG artifact
     - A CI job with pyfcstm and an approved PlantUML backend.
     - ``pyfcstm visualize -i machine.fcstm -t svg -o artifacts/machine.svg --no-open``.
     - The SVG file exists; stdout reports the renderer and output path; no desktop viewer is required.
     - If renderer discovery fails, run ``pyfcstm visualize --check --renderer auto`` and decide whether local or remote rendering is allowed.
   * - Keep a private diagram local
     - A confidential model and a local PlantUML jar.
     - ``pyfcstm visualize -i private.fcstm --renderer local -p ./plantuml.jar -t png -o private.png --no-open``.
     - The PNG is written without sending PlantUML source to a remote service.
     - If local rendering fails, fix Java/JAR paths; do not switch to ``auto`` unless remote fallback is acceptable.
   * - Diagnose an option parse error
     - A command using ``-c`` overrides.
     - ``pyfcstm plantuml -i machine.fcstm -c max_depth=abc`` as a deliberate failing probe.
     - The command should name the invalid key/value instead of writing misleading source.
     - Replace the value with an integer or remove the override.

Visual acceptance examples
~~~~~~~~~~~~~~~~~~~~~~~~~~

After producing a diagram, review the actual rendered HTML or image, not only
the source command. Use this short acceptance rubric:

1. The caption states the question answered by the diagram.
2. The selected preset matches that question: ``minimal`` for hierarchy,
   ``normal`` for transitions, ``full`` only when lifecycle/action detail is
   the point.
3. Text is readable at the documentation width. If not, reduce detail before
   increasing image size.
4. The rendering path is acceptable for the data: local for private models,
   remote only when source text may leave the machine.
5. The page links to :doc:`/reference/visualization_options/index` for every
   option that is not self-evident.

Troubleshoot visualization
--------------------------

.. list-table:: Visualization troubleshooting
   :header-rows: 1

   * - Symptom
     - Check
     - Likely fix
   * - ``plantuml`` fails
     - ``pyfcstm inspect -i machine.fcstm``
     - Fix DSL syntax or model diagnostics before diagram export.
   * - ``visualize`` fails before rendering
     - Output suffix and ``--type``
     - Align suffix and type, or omit suffix and let pyfcstm add it.
   * - Local rendering fails
     - ``pyfcstm visualize --check --renderer local``
     - Configure Java and ``PLANTUML_JAR`` or pass ``-p``.
   * - Remote rendering fails
     - ``pyfcstm visualize --check --renderer remote``
     - Check network, proxy, or ``PLANTUML_HOST``.
   * - Viewer launch is skipped
     - ``PYFCSTM_NO_GUI``, ``CI``, display variables
     - Use ``--no-open`` in scripts; reserve ``--strict-open`` for desktop-only tasks.
   * - Diagram is too dense
     - Detail level and visibility options
     - Start with ``minimal`` or ``normal``, then add only the facts needed for the current audience.
