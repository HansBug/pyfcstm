.. _sec-how-to-visualization:

Visualization tasks
===================

Use this guide when you need diagram source or rendered diagram files. For the
complete option table, see :doc:`/reference/visualization_options/index`. For a
first diagram walkthrough, see :doc:`/tutorials/visualization/index`.

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
