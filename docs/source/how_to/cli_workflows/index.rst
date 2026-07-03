.. _sec-how-to-cli-workflows:

CLI workflows
=============

Use this guide when you know the task you want to complete. For exact option
facts, see :doc:`/reference/cli/index`.

Get help for commands
---------------------

Start with the top-level help, then inspect the subcommand you want to use:

.. code-block:: bash

   pyfcstm --help
   pyfcstm simulate --help
   pyfcstm inspect --help
   pyfcstm generate --help
   pyfcstm plantuml --help

Run a short simulation
----------------------

Use batch mode when you want a reproducible command transcript:

.. code-block:: bash

   pyfcstm simulate -i machine.fcstm -e "current; cycle; current"

Use the interactive simulator when you want to explore events and hot starts by
hand:

.. code-block:: bash

   pyfcstm simulate -i machine.fcstm

Export an inspect report
------------------------

Human output is the default:

.. code-block:: bash

   pyfcstm inspect -i machine.fcstm

Scripts should request the structured format explicitly:

.. code-block:: bash

   pyfcstm inspect -i machine.fcstm --format json -o machine.inspect.json

For LLM-assisted repair, use the LLM-oriented formats:

.. code-block:: bash

   pyfcstm inspect -i machine.fcstm --format llm-md -o machine.inspect.md

Generate code from a built-in template
--------------------------------------

For packaged built-in templates, use ``--template``:

.. code-block:: bash

   pyfcstm generate -i machine.fcstm --template python -o generated/python --clear

Use ``-t`` / ``--template-dir`` only when you intentionally provide a custom
template directory that you own.

Export PlantUML source
----------------------

Use ``plantuml`` when you want a stable source file that can be versioned or
rendered by another tool:

.. code-block:: bash

   pyfcstm plantuml -i machine.fcstm -o machine.puml

Render a final diagram directly only when your environment has a usable
PlantUML backend:

.. code-block:: bash

   pyfcstm visualize -i machine.fcstm -t svg -o machine.svg --no-open

Keep CLI projects reproducible
------------------------------

For repeated local or CI use, keep the command inputs and generated outputs
traceable:

* Use descriptive ``.fcstm`` filenames and keep related machines in a dedicated
  directory such as ``src/machines/``.
* Version control the ``.fcstm`` sources with the code that consumes their
  generated outputs.
* Use ``--clear`` only for output directories that are safe to replace, and
  review generated code before committing it. If outputs are regenerated on
  demand, add them to ``.gitignore`` instead.
* Keep a small project note or build rule that records which DSL file generates
  each output directory.
* Prefer ``--template`` for packaged built-in templates. If you intentionally
  maintain custom template directories, keep one directory per target profile,
  define language-specific render helpers in ``config.yaml``, and smoke-test the
  templates with small sample machines before production use.

Next steps
----------

* :doc:`/how_to/generation/index` covers generated-runtime tasks.
* :doc:`/how_to/inspect/index` covers CI and LLM-oriented inspect use.
* :doc:`/how_to/visualization/index` covers diagram export tasks.
