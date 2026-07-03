.. _sec-reference-builtin-templates:

Built-in templates reference
============================

Use these names with ``pyfcstm generate --template <name>``. Do not use a
repository ``templates/`` path for built-in templates.

Template matrix
---------------

.. list-table:: Built-in templates
   :header-rows: 1

   * - Template
     - Main files
     - User entry point
     - Notes
   * - ``python``
     - ``machine.py``, ``README.md``, ``README_zh.md``
     - Import the generated class from ``machine.py``.
     - Self-contained runtime for Python integration and simulator-aligned experiments.
   * - ``c``
     - ``machine.h``, ``machine.c``, generated README files
     - Include ``machine.h`` and pass explicit event-id arrays to ``cycle``.
     - Use for C integration where the application already collects events.
   * - ``c_poll``
     - ``machine.h``, ``machine.c``, generated README files
     - Install a complete ``EventChecks`` table before calling the zero-event ``cycle`` API.
     - Use for scan-loop style C integration where event truth is sampled on demand.
   * - ``cpp``
     - C core files plus ``machine.hpp`` and ``machine.cpp``
     - Include ``machine.hpp`` and use ``MachineWrapper``.
     - The C core is included, but C++ user code should not bypass the wrapper as its main entry point.
   * - ``cpp_poll``
     - C poll core files plus ``machine.hpp`` and ``machine.cpp``
     - Include ``machine.hpp``, install wrapper ``EventChecks``, and use ``MachineWrapper``.
     - Use for C++ scan-loop integration with wrapper-level event checks.

Generated README files
----------------------

All built-in templates write ``README.md`` and ``README_zh.md`` into the output
directory. Those files are part of the generated output contract and carry the
machine-specific API, hook, hot-start, and build guidance.

Target-profile note
-------------------

C-family templates use fixed-width generated integer storage in the default
profile. Inspect numeric deployment warnings therefore apply to ``c``,
``c_poll``, ``cpp``, and ``cpp_poll`` targets. They should not be presented as
proof that a Python generated runtime has the same fixed-width integer carrying
risk.

More tasks
----------

See :doc:`/how_to/generation/index` for generation and smoke-check tasks.
