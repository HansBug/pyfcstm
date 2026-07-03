.. _sec-reference-cli:

CLI reference
=============

This page lists command facts for the public ``pyfcstm`` CLI. Use
:doc:`/how_to/cli_workflows/index` when you want task steps instead of a fact
table.

Top-level command
-----------------

.. code-block:: text

   pyfcstm [OPTIONS] COMMAND [ARGS]...

.. list-table:: Top-level options
   :header-rows: 1

   * - Option
     - Meaning
   * - ``-v, --version``
     - Show package version information.
   * - ``-h, --help``
     - Show help and exit.

Commands
--------

.. list-table:: Commands
   :header-rows: 1

   * - Command
     - Purpose
   * - ``simulate``
     - Run an interactive or batch state-machine simulator.
   * - ``inspect``
     - Emit a human-readable, JSON, or LLM-oriented model inspection report.
   * - ``generate``
     - Generate source code from a custom template directory or packaged built-in template.
   * - ``plantuml``
     - Emit PlantUML source text.
   * - ``visualize``
     - Render a diagram file through a PlantUML backend.

``simulate`` options
--------------------

.. code-block:: text

   pyfcstm simulate -i <input-code> [-e "current; cycle; current"] [--no-color]

.. list-table:: ``simulate`` options
   :header-rows: 1

   * - Option
     - Required
     - Meaning
   * - ``-i, --input-code``
     - yes
     - FCSTM DSL entry file.
   * - ``-e, --execute``
     - no
     - Semicolon-separated simulator commands, then exit.
   * - ``--no-color``
     - no
     - Disable color output.

``inspect`` options
-------------------

.. code-block:: text

   pyfcstm inspect -i <input-code> [-o <output>] [--format human|json|llm-json|llm-md]

.. list-table:: ``inspect`` options
   :header-rows: 1

   * - Option
     - Default
     - Meaning
   * - ``-i, --input-code``
     - required
     - FCSTM DSL entry file.
   * - ``-o, --output``
     - stdout
     - Output file path.
   * - ``--format``
     - ``human``
     - Output format: ``human``, ``json``, ``llm-json``, or ``llm-md``.
   * - ``--color``
     - ``auto``
     - ANSI color policy for human output only: ``auto``, ``always``, or ``never``.
   * - ``--enable-verify``
     - off
     - Add inspect-eligible verify diagnostics.
   * - ``--max-complexity-tier``
     - ``structural``
     - Highest verify complexity tier accepted by inspect.
   * - ``--max-call-count-scaling``
     - ``linear_in_transitions``
     - Highest verify call-count scaling accepted by inspect.
   * - ``--smt-timeout-ms``
     - not set
     - Optional SMT solver timeout in milliseconds; ``0`` keeps Z3 without a finite timeout.

``generate`` options
--------------------

.. code-block:: text

   pyfcstm generate -i <input-code> --template <name> -o <output-dir> [--clear]
   pyfcstm generate -i <input-code> -t <template-dir> -o <output-dir> [--clear]

Use ``--template`` for packaged built-in templates. Use ``-t`` /
``--template-dir`` only for custom template directories that you maintain.

.. list-table:: ``generate`` options
   :header-rows: 1

   * - Option
     - Required
     - Meaning
   * - ``-i, --input-code``
     - yes
     - FCSTM DSL entry file.
   * - ``--template``
     - one of ``--template`` or ``-t``
     - Packaged built-in template: ``python``, ``c``, ``c_poll``, ``cpp``, or ``cpp_poll``.
   * - ``-t, --template-dir``
     - one of ``--template`` or ``-t``
     - Custom template directory. Use this only when you intentionally own the template directory.
   * - ``-o, --output-dir``
     - yes
     - Generated output directory.
   * - ``--clear, --clear-directory``
     - no
     - Clear the output directory before rendering.

``plantuml`` options
--------------------

.. code-block:: text

   pyfcstm plantuml -i <input-code> [-o <output>] [-l minimal|normal|full] [-c key=value]

.. list-table:: ``plantuml`` options
   :header-rows: 1

   * - Option
     - Default
     - Meaning
   * - ``-i, --input-code``
     - required
     - FCSTM DSL entry file.
   * - ``-o, --output``
     - stdout
     - PlantUML source output path.
   * - ``-l, --level``
     - ``normal``
     - Detail preset: ``minimal``, ``normal``, or ``full``.
   * - ``-c, --config``
     - none
     - PlantUML option override in ``key=value`` form; may be repeated.

``visualize`` options
---------------------

.. code-block:: text

   pyfcstm visualize -i <input-code> [-o <output>] [-t png|svg|pdf] [--renderer auto|local|remote]

.. list-table:: ``visualize`` options
   :header-rows: 1

   * - Option
     - Default
     - Meaning
   * - ``-i, --input-code``
     - required unless ``--check`` is used
     - FCSTM DSL entry file.
   * - ``-o, --output``
     - cache path
     - Rendered output file.
   * - ``-l, --level``
     - ``normal``
     - Detail preset shared with ``plantuml``.
   * - ``-c, --config``
     - none
     - PlantUML option override in ``key=value`` form; may be repeated.
   * - ``-t, --type``
     - ``png``
     - Rendered diagram type: ``png``, ``svg``, or ``pdf``.
   * - ``--renderer``
     - ``auto``
     - Renderer backend: ``auto``, ``local``, or ``remote``.
   * - ``-j, --java``
     - ``java`` from ``PATH``
     - Java executable for local rendering.
   * - ``-p, --plantuml, --plantuml-jar``
     - ``PLANTUML_JAR`` or unset
     - PlantUML jar path for local rendering.
   * - ``-r, --remote-host``
     - PlantUML public server default
     - Remote PlantUML service base URL.
   * - ``--check``
     - off
     - Check renderer availability and exit without rendering.
   * - ``--open / --no-open``
     - command default
     - Open or do not open the rendered file with the system viewer.
   * - ``--strict-open``
     - off
     - Treat viewer-launch failure as an error.
