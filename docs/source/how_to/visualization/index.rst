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

Use Python API when needed
--------------------------

CLI ``-c`` supports typed scalar and tuple options. Use the Python API for
object-valued configuration such as custom color dictionaries:

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
