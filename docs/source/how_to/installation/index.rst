.. _sec-how-to-installation:

Install pyfcstm
===============

Use this guide when you want a working ``pyfcstm`` command on a local
machine or CI runner. The project supports Python 3.7 through 3.14, so the
commands below avoid new Python-only tooling assumptions.

Install from PyPI
-----------------

For normal use, install the published package:

.. code-block:: bash

   python -m pip install pyfcstm

If your environment keeps several Python interpreters, use the exact
interpreter that will run the CLI:

.. code-block:: bash

   python3 -m pip install pyfcstm

Install from the main branch
----------------------------

Use the GitHub source install only when you intentionally want the latest
repository state instead of the latest PyPI release:

.. code-block:: bash

   python -m pip install -U git+https://github.com/hansbug/pyfcstm@main

Use a pre-built executable
--------------------------

If your deployment environment cannot install Python packages directly, check
the `GitHub Releases page <https://github.com/HansBug/pyfcstm/releases>`_ for
pre-built executable artifacts. Prefer PyPI for normal development and CI, and
use release artifacts only when that packaging model fits your environment.

Verify the Python package
-------------------------

The installation tutorial keeps a checked-in verification script. You can run
the same idea in any project by importing the package metadata:

.. literalinclude:: ../../tutorials/installation/install_check.demo.py
   :language: python
   :linenos:

Expected output shape:

.. literalinclude:: ../../tutorials/installation/install_check.demo.py.txt
   :language: text
   :linenos:

Verify the CLI
--------------

Check the top-level command first:

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

Troubleshooting checklist
-------------------------

* If ``pyfcstm`` is not on ``PATH``, run ``python -m pyfcstm --help`` with the
  interpreter that installed the package.
* If a CI job uses a virtual environment, install pyfcstm after activating that
  environment.
* If you need rendered PlantUML images, install and configure a PlantUML
  backend separately. Core commands such as ``simulate``, ``inspect``,
  ``generate``, and ``plantuml`` source export do not require a local renderer.

Next steps
----------

* :doc:`/tutorials/quick_start/index` gives the shortest end-to-end path.
* :doc:`/how_to/cli_workflows/index` shows common command-line tasks.
* :doc:`/reference/cli/index` lists the command and option facts.
* Published documentation is available at
  `hansbug.github.io/pyfcstm <https://hansbug.github.io/pyfcstm/main/index.html>`_.
