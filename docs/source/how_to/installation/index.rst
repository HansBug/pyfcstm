.. _sec-how-to-installation:

Install pyfcstm
===============

Use this guide when you need a working ``pyfcstm`` command on a local machine
or CI runner. The package supports Python 3.7 through 3.14, so the commands
avoid assumptions that only work on the newest Python releases.

What installation includes
--------------------------

The normal package installation is an all-in-one install for the current public
runtime dependencies. It installs the CLI, parser, model layer, simulator,
renderer, diagnostics, verify support, and visualization integration declared by
the package. It does not install external system programs such as Java, PlantUML
jar files, Graphviz, or desktop viewers.

.. list-table:: Capability after package install
   :header-rows: 1

   * - Capability
     - Included in Python package install
     - External tool sometimes needed
   * - Parse DSL and build models
     - yes
     - no
   * - ``simulate``
     - yes
     - no
   * - ``inspect`` and bounded verify integration
     - yes
     - no extra system tool for normal inspect use
   * - ``generate`` with packaged templates
     - yes
     - no for Python generation; target compilers are needed only when you build generated C/C++ artifacts
   * - ``plantuml`` source export
     - yes
     - no
   * - ``visualize`` rendered output
     - Python integration yes
     - Java and a PlantUML jar for local rendering, or network access to a remote PlantUML service

Install from PyPI
-----------------

For normal use, install the published package with the interpreter that will run
the CLI:

.. code-block:: bash

   python -m pip install pyfcstm

If the machine has several Python interpreters, be explicit:

.. code-block:: bash

   python3 -m pip install pyfcstm
   python3 -m pyfcstm --help

For project-local work, prefer a virtual environment:

.. code-block:: bash

   python -m venv .venv
   . .venv/bin/activate
   python -m pip install -U pip
   python -m pip install pyfcstm
   pyfcstm --help

On Windows ``cmd.exe``, activation usually looks like:

.. code-block:: bat

   py -m venv .venv
   .venv\Scripts\activate
   python -m pip install -U pip
   python -m pip install pyfcstm
   pyfcstm --help

Install from the main branch
----------------------------

Use a source install only when you intentionally need the current repository
state instead of the latest PyPI release:

.. code-block:: bash

   python -m pip install -U git+https://github.com/hansbug/pyfcstm@main

Pin a branch, tag, or commit in project automation. Unpinned source installs can
change without your build configuration changing.

Use a pre-built executable
--------------------------

If the deployment environment cannot install Python packages directly, check the
`GitHub Releases page <https://github.com/HansBug/pyfcstm/releases>`_ for
pre-built executable artifacts. Prefer PyPI for normal development and CI; use
release artifacts only when that packaging model fits the deployment target.

Verify the Python package
-------------------------

The installation tutorial keeps a checked-in verification script. It imports the
package metadata and proves that Python can load the installed package:

.. literalinclude:: ../../tutorials/installation/install_check.demo.py
   :language: python
   :linenos:

Expected output shape:

.. literalinclude:: ../../tutorials/installation/install_check.demo.py.txt
   :language: text
   :linenos:

For a shorter manual check, run:

.. code-block:: bash

   python - <<'PY'
   import pyfcstm
   print(pyfcstm.__title__)
   print(pyfcstm.__version__)
   PY

Verify the CLI
--------------

Check version and help first:

.. code-block:: bash

   pyfcstm -v
   pyfcstm --help

The documentation build also exercises this shell check:

.. literalinclude:: ../../tutorials/installation/cli_check.demo.sh
   :language: shell
   :linenos:

.. literalinclude:: ../../tutorials/installation/cli_check.demo.sh.txt
   :language: text
   :linenos:

Verify a tiny DSL round trip
----------------------------

After the command exists, test the parser and one non-rendering command with a
small file:

.. code-block:: bash

   cat > smoke.fcstm <<'FCSTM'
   state Root {
       state Idle;
       [*] -> Idle;
   }
   FCSTM
   pyfcstm inspect -i smoke.fcstm
   pyfcstm plantuml -i smoke.fcstm -o smoke.puml

This check does not need Java, PlantUML, a compiler, or a graphical desktop.

Optional renderer setup
-----------------------

``pyfcstm plantuml`` writes PlantUML source and needs no renderer. Only
``pyfcstm visualize`` needs a renderer backend.

For local rendering, install Java and provide a PlantUML jar:

.. code-block:: bash

   export PLANTUML_JAR=/path/to/plantuml.jar
   pyfcstm visualize --check --renderer local

For remote rendering, configure a PlantUML service when you do not want the
public default:

.. code-block:: bash

   export PLANTUML_HOST=http://www.plantuml.com/plantuml
   pyfcstm visualize --check --renderer remote

Remote rendering sends generated PlantUML source to the configured service. Use
local rendering for private diagrams.

CI installation pattern
-----------------------

In CI, keep package installation separate from command execution so failures are
easier to diagnose:

.. code-block:: bash

   python -m pip install -U pip
   python -m pip install pyfcstm
   python -m pyfcstm --help
   pyfcstm inspect -i machines/main.fcstm --format json -o build/main.inspect.json

For rendered diagrams in CI, avoid viewer launch:

.. code-block:: bash

   pyfcstm visualize -i machines/main.fcstm -t svg -o build/main.svg --no-open

Troubleshooting checklist
-------------------------

.. list-table:: Installation troubleshooting
   :header-rows: 1

   * - Symptom
     - Likely cause
     - Fix
   * - ``pyfcstm`` is not found
     - The script directory is not on ``PATH`` or the wrong interpreter installed the package.
     - Run ``python -m pyfcstm --help`` with the intended interpreter, then fix environment activation or ``PATH``.
   * - ``python -m pyfcstm`` fails to import
     - Package not installed in that interpreter.
     - Run ``python -m pip show pyfcstm`` and reinstall with the same interpreter.
   * - CLI exists but a DSL command fails
     - Input path, syntax, or model validation issue.
     - Run ``pyfcstm inspect -i <file>`` and use the diagnostics output.
   * - ``visualize --check --renderer local`` fails
     - Missing Java, missing PlantUML jar, invalid jar path, or local backend failure.
     - Install Java, set ``PLANTUML_JAR``, or pass ``-p /path/to/plantuml.jar``.
   * - ``visualize --check --renderer remote`` fails
     - Network, proxy, or remote service issue.
     - Set ``PLANTUML_HOST`` to an allowed service or use local rendering.
   * - Viewer does not open after render
     - Headless environment or no system opener.
     - Use ``--no-open`` in scripts; use ``--strict-open`` only when opening is required.

Next steps
----------

* :doc:`/tutorials/quick_start/index` gives the shortest end-to-end path.
* :doc:`/how_to/cli_workflows/index` shows common command-line tasks.
* :doc:`/reference/cli/index` lists command and option facts.
* Published documentation is available at
  `hansbug.github.io/pyfcstm <https://hansbug.github.io/pyfcstm/main/index.html>`_.
