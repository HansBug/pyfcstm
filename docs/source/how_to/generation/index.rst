.. _sec-how-to-generation:

Generation tasks
================

Use this guide when the job is to run ``pyfcstm generate`` and smoke-check the
result. It is for generated-code users. Template authors should use
:doc:`../templates/index`; exact template contracts live in
:doc:`../../reference/builtin_templates/index`.

Current built-in status
-----------------------

pyfcstm currently packages five built-in templates: ``python``, ``c``,
``c_poll``, ``cpp``, and ``cpp_poll``. Each current built-in template has
``experimental: true`` in packaged metadata. That flag does not mean the
template is a stub; it means the output is an engineering baseline with the
current test evidence, not a production certification or every-platform native
compiler guarantee.

Choose the generation entry point
---------------------------------

``pyfcstm generate`` requires exactly one template source:

.. list-table:: Template source choice
   :header-rows: 1

   * - Use this option
     - When to use it
     - Boundary
   * - ``--template <name>``
     - You want an installed built-in template.
     - This is the stable user path for built-ins.
   * - ``-t <dir>`` / ``--template-dir <dir>``
     - You are authoring or testing a custom template directory.
     - Do not teach ordinary users to point this at repository ``templates/``.

Passing both options is a usage error. Passing neither is also a usage error.
Passing an unknown built-in name is rejected by Click before rendering starts.

Prepare an input model
----------------------

The examples use the same small model as the first tutorial:

.. literalinclude:: ../../tutorials/generation/simple_machine.fcstm
   :language: fcstm

Generate each built-in template
-------------------------------

Use one short command per target:

.. code-block:: bash

   pyfcstm generate -i simple_machine.fcstm --template python -o generated/python --clear
   pyfcstm generate -i simple_machine.fcstm --template c -o generated/c --clear
   pyfcstm generate -i simple_machine.fcstm --template c_poll -o generated/c_poll --clear
   pyfcstm generate -i simple_machine.fcstm --template cpp -o generated/cpp --clear
   pyfcstm generate -i simple_machine.fcstm --template cpp_poll -o generated/cpp_poll --clear

The ``--clear`` option deletes the previous contents of the output directory
before rendering. Use it for repeatable examples and CI scratch directories.
Do not use it on a directory that contains files you want to keep.

Read the generated README first
-------------------------------

Every built-in template emits ``README.md`` and ``README_zh.md`` into the
output directory. Those files are generated from your model and are the
machine-specific integration guide. The reference pages document the general
contract; the generated README tells you the actual class names, event ids,
hook names, state ids, hot-start examples, and build snippets for that model.

The generated top-level files are:

.. list-table:: Generated file summary
   :header-rows: 1

   * - Template
     - Files
     - Main user entry point
   * - ``python``
     - ``machine.py``, ``README.md``, ``README_zh.md``
     - Import the generated machine class from ``machine.py``.
   * - ``c``
     - ``machine.h``, ``machine.c``, generated README files
     - Include ``machine.h`` and pass event-id arrays to ``..._cycle``.
   * - ``c_poll``
     - ``machine.h``, ``machine.c``, generated README files
     - Install ``EventChecks`` and call the zero-argument event-polling cycle.
   * - ``cpp``
     - C core files plus ``machine.hpp`` / ``machine.cpp`` and README files
     - Include ``machine.hpp`` and use ``MachineWrapper``.
   * - ``cpp_poll``
     - C polling core files plus ``machine.hpp`` / ``machine.cpp`` and README files
     - Include ``machine.hpp``, install wrapper event checks, and use ``MachineWrapper``.

Smoke-check Python output
-------------------------

A minimal Python consumer imports ``machine.py`` and advances through a few
events:

.. literalinclude:: ../../tutorials/generation/python_runtime.demo.py
   :language: python
   :lines: 47-60

The checked-in demo prints:

.. literalinclude:: ../../tutorials/generation/python_runtime.demo.py.txt
   :language: text

This evidence means the generated Python runtime is importable and can execute
the shown event sequence. Broader simulator alignment is covered by template
unit tests, not by this one tutorial smoke check.

Smoke-check C and C++ outputs
-----------------------------

The native demonstration in the documentation tree generates ``c``,
``c_poll``, ``cpp``, and ``cpp_poll`` outputs and builds small drivers when
``cc``, ``c++``, and ``cmake`` are available. Its output starts with the local
toolchain snapshot and then prints one section per template:

.. literalinclude:: ../../tutorials/generation/native_runtime.demo.sh.txt
   :language: text
   :lines: 1-28

This is a local smoke check. It proves that the generated files compiled and ran
on the displayed toolchain. It is not a claim that every embedded compiler,
industrial profile, sanitizer profile, or certification environment has been
validated.

Choose explicit events or polling
---------------------------------

The non-polling templates expect the application to submit events for each
cycle:

.. list-table:: Event input model
   :header-rows: 1

   * - Template family
     - Event model
     - Use when
   * - ``python``
     - ``cycle(events=None)`` accepts no event, one event string, or a collection.
     - Python application code already knows which event paths are active.
   * - ``c`` / ``cpp``
     - The cycle call receives generated integer event ids.
     - Your integration layer collects events before calling the runtime.
   * - ``c_poll`` / ``cpp_poll``
     - The runtime calls installed event-check callbacks during a cycle.
     - Your host reads event truth from callbacks, device probes, or application state.

Use ``c_poll`` or ``cpp_poll`` only when the polling shape is the desired
integration surface. Do not treat it as a semantic fork of FCSTM execution; it
is the event input mechanism that changes.

Troubleshoot common generation failures
---------------------------------------

.. list-table:: Failure checklist
   :header-rows: 1

   * - Symptom
     - Likely cause
     - Repair
   * - ``Invalid value for '--template'``
     - The built-in template name is not in the installed package.
     - Run ``pyfcstm generate --help`` or use ``pyfcstm.template.list_templates()``.
   * - ``Exactly one of --template-dir/-t or --template must be provided.``
     - Both template options were passed, or neither was passed.
     - Pick the built-in path or the custom-template path, not both.
   * - YAML / config validation error
     - A custom template ``config.yaml`` has an invalid root, section, style, or ignore rule.
     - Use :doc:`../../reference/template_config/index` to find the failing shape.
   * - Template rendering error
     - A Jinja expression, helper import, model attribute, or custom filter failed.
     - Reduce to a small model and template file; then check helper registration.
   * - Generated native code does not compile
     - The output contract, compiler, flags, or integration driver do not match.
     - Start from the generated README and the smallest driver before adding application code.

Verify a documentation or template change
-----------------------------------------

Use the smallest evidence that matches the claim:

.. list-table:: Evidence levels
   :header-rows: 1

   * - Claim
     - Useful check
     - Boundary
   * - Generation command works
     - Run ``pyfcstm generate`` on a small ``.fcstm`` file.
     - Does not prove runtime semantics.
   * - Python output is usable
     - Import ``machine.py`` and run a few cycles.
     - Does not prove every semantic fixture.
   * - Native output compiles locally
     - Configure/build/run a small CMake or driver smoke check.
     - Toolchain-specific evidence only.
   * - Template claims simulator parity
     - Run the semantic-alignment tests for that template family.
     - Must state event-model exclusions and fixture coverage.
