First diagram
=============

This tutorial shows the shortest path from an FCSTM model to a PlantUML diagram
source file and rendered example. For export recipes, see
:doc:`/how_to/visualization/index`; for option facts, see
:doc:`/reference/visualization_options/index`.

Example state machine
---------------------

.. literalinclude:: example.fcstm
   :language: fcstm
   :caption: example.fcstm

Generate PlantUML source
------------------------

Use ``plantuml`` when you want deterministic text output:

.. literalinclude:: cli_basic.demo.sh
   :language: bash
   :caption: Basic CLI visualization

Expected feedback:

.. literalinclude:: cli_basic.demo.sh.txt
   :language: text

Rendered example
----------------

The documentation resource build renders the generated PlantUML source into an
SVG artifact:

.. figure:: output_cli_basic.puml.svg
   :alt: CLI basic visualization output
   :align: center
   :width: 80%

   PlantUML diagram generated with CLI default settings.

Try detail presets
------------------

Use ``-l`` for the built-in detail presets:

.. code-block:: bash

   pyfcstm plantuml -i example.fcstm -l minimal -o output_minimal.puml
   pyfcstm plantuml -i example.fcstm -l normal -o output_normal.puml
   pyfcstm plantuml -i example.fcstm -l full -o output_full.puml

The option reference explains which facts each preset affects.

Where to go next
----------------

* :doc:`/how_to/visualization/index` shows PlantUML source export and direct
  rendered-file export tasks.
* :doc:`/reference/visualization_options/index` lists ``PlantUMLOptions`` and
  CLI ``-c`` facts.
* :doc:`/tutorials/quick_start/index` includes visualization in the shortest
  end-to-end path.
