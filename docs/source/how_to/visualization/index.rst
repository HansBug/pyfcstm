.. _sec-how-to-visualization:

Visualization tasks
===================

Use this guide when you want to export diagram artifacts. For option facts, see
:doc:`/reference/visualization_options/index`.

Export PlantUML source
----------------------

PlantUML source is deterministic and easy to review:

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm -o machine.puml

Use detail presets with ``-l``:

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm -l full -o machine.full.puml

Override typed options with repeated ``-c key=value`` arguments:

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm \
     -c show_events=true \
     -c max_depth=3 \
     -o machine.events.puml


Compare detail preset outputs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The same machine can produce different diagrams for different audiences:

.. list-table:: Detail preset comparison
   :header-rows: 1

   * - Preset
     - Intended view
     - Existing rendered example
   * - ``minimal``
     - Basic state structure only.
     - :download:`output_minimal.puml <../../tutorials/visualization/output_minimal.puml>`
   * - ``normal``
     - Balanced view with essential lifecycle and transition information.
     - :download:`output_normal.puml <../../tutorials/visualization/output_normal.puml>`
   * - ``full``
     - Complete details, including actions, events, guards, and effects.
     - :download:`output_full.puml <../../tutorials/visualization/output_full.puml>`

.. figure:: ../../tutorials/visualization/output_minimal.puml.svg
   :alt: Minimal detail preset output
   :align: center
   :width: 70%

   ``minimal``: basic state structure.

.. figure:: ../../tutorials/visualization/output_normal.puml.svg
   :alt: Normal detail preset output
   :align: center
   :width: 70%

   ``normal``: balanced default view.

.. figure:: ../../tutorials/visualization/output_full.puml.svg
   :alt: Full detail preset output
   :align: center
   :width: 70%

   ``full``: implementation-oriented detail.

Render a final file directly
----------------------------

Use ``visualize`` when your environment has a local or remote PlantUML renderer:

.. code-block:: bash

   pyfcstm visualize -i machine.fcstm -t svg -o machine.svg --no-open

Check renderer availability without rendering:

.. code-block:: bash

   pyfcstm visualize --check --renderer auto

Choose a renderer mode
----------------------

* ``--renderer auto`` tries local rendering first and falls back to remote rendering.
* ``--renderer local`` uses Java and a PlantUML jar.
* ``--renderer remote`` uses a PlantUML service.

In CI or other headless environments, prefer ``--no-open`` so viewer launch is
not part of the job result.

Keep diagrams readable
----------------------

Treat visualization as audience-specific output instead of a single canonical
diagram:

* Use ``minimal`` for high-level architecture overviews or non-technical
  stakeholders.
* Use ``normal`` for general documentation and code review.
* Use ``full`` for detailed implementation documentation and debugging.
* Start with defaults, then add options only when the diagram answers a clearer
  question.
* For large state machines, use ``max_depth`` to focus on the levels currently
  under review.
* Hide lifecycle actions, transition effects, or events that are not relevant to
  the current audience.
* Enable ``event_visualization_mode=color`` when event tracking is more useful
  than plain transition labels.
* Use ``collapse_empty_states`` to reduce visual clutter in sparse or structural
  diagrams.

Large models can produce large PlantUML files. For initial exploration, prefer a
limited-depth diagram and generate separate diagrams at different detail levels
for different audiences.

Use Python API when needed
--------------------------

CLI ``-c`` supports typed scalar and tuple options. Use the Python API for
object-valued configuration such as custom color dictionaries. The snippet below
assumes you already have a parsed ``model`` object; use the downloadable demo for
a complete runnable script:

.. code-block:: python

   from pyfcstm.model.plantuml import PlantUMLOptions

   options = PlantUMLOptions(
       event_visualization_mode='color',
       custom_colors={'System.Start': '#00AA00'},
   )
   plantuml_text = model.to_plantuml(options)

For full runnable examples, download
:download:`python_basic.demo.py <../../tutorials/visualization/python_basic.demo.py>`
and
:download:`python_options.demo.py <../../tutorials/visualization/python_options.demo.py>`.
