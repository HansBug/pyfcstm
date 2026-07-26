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

Open the offline Python viewer
------------------------------

The Python ``Diagram`` facade is the browser-based path when you want a
self-contained HTML file with source/diagram comparison and browser-side SVG,
PNG, and vector PDF downloads. It does not require PlantUML or Node at runtime.

.. code-block:: python

   from pyfcstm.model import load_state_machine_from_text

   model = load_state_machine_from_text("state Root { state Idle; [*] -> Idle; }")
   diagram = model.diagram(direction="LR", cjk_locale="sc")
   data = diagram.to_dict()
   html = diagram.to_html()
   output = diagram.show(open_window=False)

The first three values are, respectively, portable data, complete HTML text,
and a generated ``.html`` path. The HTML file contains the viewer, renderer,
WASM, and selected fonts, so it remains usable without a network connection.
Use ``open_window=True`` (the default) only when a Chromium-family browser is
available. Without one, ``show`` raises ``DiagramUnavailableError``; use
``open_window=False`` to create the file without opening a window.

The synchronous ``to_svg()``, ``to_png()``, and ``to_pdf()`` methods are typed
capability probes in this stage and raise ``DiagramUnavailableError``. The
browser export buttons in the generated HTML are the available three-format
export path; the optional headless Python runtime is owned by the later delivery
stage.

Where to go next
----------------

* :doc:`/how_to/visualization/index` shows PlantUML source export and direct
  rendered-file export tasks, plus the Python Diagram viewer workflow.
* :doc:`/reference/visualization_options/index` lists ``PlantUMLOptions`` and
  CLI ``-c`` facts and the Python Diagram option/value contracts.
* :doc:`/tutorials/quick_start/index` includes visualization in the shortest
  end-to-end path.
