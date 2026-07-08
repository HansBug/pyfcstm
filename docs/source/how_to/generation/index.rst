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

Treat the generated README as the handoff from documentation to integration. If
the generic reference and the generated README appear to disagree, start with
the generated README for names that depend on your machine, then use the
reference to check whether the template family, event input model, or evidence
boundary was misread.

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
     - Install ``EventChecks`` and call the machine-argument polling cycle without an event-id array.
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

When the native demonstration fails, record the toolchain snapshot first, then
decide whether the failure is a generator issue, a missing build tool, or a
custom driver that disagrees with the generated README. Template maintainers
need the template name, output directory, compiler versions, and smallest driver,
not only the final compiler error line.

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

For the same model, start with the template whose event input is easiest to
drive in the host application. Switching later is possible, but the consumer
code, hook installation, and native smoke command should be updated together so
that the generated README remains the single integration checklist.

In a change record, write down three facts: which template was chosen, how the
host supplies events, and which command proved the generated output usable. That
keeps later readers from reverse-engineering the integration surface from the
output tree and helps separate event-input mistakes from hook or build issues.

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

Task acceptance cards
---------------------

Use these cards when reviewing whether a generation recipe is complete. Each
card names the starting input, the command, the success signal, the side effect,
and the first repair step.

.. list-table:: Built-in generation task cards
   :header-rows: 1

   * - Task
     - Command
     - Success signal
     - Side effect and first repair
   * - Generate the Python runtime.
     - ``pyfcstm generate -i docs/source/tutorials/generation/simple_machine.fcstm --template python -o /tmp/pyfcstm-python --clear``
     - ``machine.py`` and generated README files exist; the README names the concrete class.
     - ``--clear`` replaces the scratch output. If it fails, confirm the input parses before inspecting the template.
   * - Generate explicit-event C output.
     - ``pyfcstm generate -i docs/source/tutorials/generation/simple_machine.fcstm --template c -o /tmp/pyfcstm-c --clear``
     - ``machine.h`` and ``machine.c`` exist, and the README shows event ids.
     - A later compiler smoke must use the generated header. If event names are unclear, read the generated README rather than guessing ids.
   * - Generate polling C output.
     - ``pyfcstm generate -i docs/source/tutorials/generation/simple_machine.fcstm --template c_poll -o /tmp/pyfcstm-c-poll --clear``
     - ``machine.h`` documents the event-check table shape.
     - Polling requires callbacks for event truth. If events never fire, inspect ``EventChecks`` before editing state-machine logic.
   * - Generate the C++ wrapper.
     - ``pyfcstm generate -i docs/source/tutorials/generation/simple_machine.fcstm --template cpp -o /tmp/pyfcstm-cpp --clear``
     - ``machine.hpp`` and ``machine.cpp`` appear in addition to the C core.
     - User code should include ``machine.hpp``. If a build bypasses the wrapper, the smoke no longer proves the documented C++ surface.
   * - Generate the C++ polling wrapper.
     - ``pyfcstm generate -i docs/source/tutorials/generation/simple_machine.fcstm --template cpp_poll -o /tmp/pyfcstm-cpp-poll --clear``
     - Wrapper files plus polling README guidance are emitted.
     - Install wrapper-facing event checks. If a transition stays inactive, verify the callback return values for that cycle.
   * - Re-render into a clean scratch directory.
     - Add ``--clear`` only when the output directory is disposable.
     - Old generated files vanish and the new tree contains only current output.
     - If a hand-written file disappeared, restore it from version control and stop using that directory as a scratch output.
   * - Use a custom template directory.
     - ``pyfcstm generate -i model.fcstm -t ./my_template -o ./out --clear``
     - The renderer consumes ``./my_template/config.yaml`` and the ``*.j2`` files in that directory.
     - This path is for template authors. If you wanted a packaged template, use ``--template`` instead.
   * - Keep a machine-specific integration note.
     - Open the generated ``README.md`` after every generation.
     - The README lists concrete API names, hook names, ids, and build snippets for this model.
     - If a generic reference and generated README appear to disagree on names, prefer the generated README for that machine and report the mismatch.

Template-selection checklist
----------------------------

.. list-table:: Choosing a built-in target
   :header-rows: 1

   * - Need
     - Prefer
     - Do not assume
   * - Pure Python integration and quick semantic smoke.
     - ``python``.
     - Do not assume this proves C-family integer or compiler behavior.
   * - C host that already knows which events are active each cycle.
     - ``c``.
     - Do not install polling callbacks and expect the explicit-event API to call them.
   * - C host where events should be queried from callbacks.
     - ``c_poll``.
     - Do not treat callback polling as a different state-machine semantics.
   * - C++ application that wants a wrapper but accepts a generated C core.
     - ``cpp``.
     - Do not describe it as a fully independent C++ runtime.
   * - C++ application that wants wrapper-facing polling callbacks.
     - ``cpp_poll``.
     - Do not test only the C core and call the wrapper contract verified.

Failure drills with exact first checks
--------------------------------------

.. list-table:: Generation failure drills
   :header-rows: 1

   * - Drill
     - Example trigger
     - First check
     - Why this check is first
   * - Unknown built-in template.
     - ``--template py``.
     - Run a tiny Python snippet with ``pyfcstm.template.list_templates()`` or inspect ``pyfcstm generate --help``.
     - The error happens before template extraction, so editing output files cannot help.
   * - Both template paths selected.
     - ``--template python -t ./template``.
     - Remove one option and rerun the same input.
     - The CLI intentionally requires exactly one template source to avoid ambiguous trust and packaging boundaries.
   * - Invalid custom ``config.yaml``.
     - A top-level key such as ``helperz``.
     - Compare the file with :doc:`../../reference/template_config/index` before changing Jinja templates.
     - Config validation runs before file rendering, so Jinja syntax is not the first suspect.
   * - Jinja render failure.
     - ``{{ state.unknown_attr }}`` in a template file.
     - Reduce to one template file and one small model, then inspect the model object used by the existing templates.
     - The renderer already parsed the model; the failing layer is the trusted template expression or helper.
   * - Native build failure.
     - Missing include path, wrong compiler mode, or incomplete hook table.
     - Reproduce with the generated README build snippet and the smallest driver.
     - A failing application build may combine generator output with unrelated build-system assumptions.

Native smoke policy for docs
----------------------------

The checked documentation script ``native_runtime.demo.sh`` is the canonical
small native smoke for this tutorial family. A PR that changes generation,
C-family template docs, or native claims should either run it or state the exact
reason it could not run in that environment.

When it runs, record the toolchain lines and the per-template success section.
When it cannot run, do not silently convert the claim into prose. State which
binary is missing, for example ``cmake``, ``cc`` or ``c++``, and keep the claim
at the generation level rather than the native-runtime level.

Reader handoff after generation
-------------------------------

After the first successful command, hand the reader to the page that owns the
next question:

* use :doc:`../../reference/builtin_templates/index` to compare built-in target
  contracts and experimental status;
* use :doc:`../templates/index` when the next step is authoring a custom
  template directory;
* use :doc:`../../reference/template_config/index` when a ``config.yaml`` key,
  style, helper, or ignore rule needs exact lookup;
* use :doc:`../../explanations/template_rendering/index` when the reader needs
  to understand why built-in and custom templates share the same renderer;
* use the generated README when integrating one generated machine into an
  application.

Reusable validation checklist
-----------------------------

When documenting generation workflows for a project, record these facts near the
change summary or in the team validation notes:

* exact pages edited and which reader role each page owns;
* the ``simple_machine.fcstm`` generation command used for the Python consumer
  smoke;
* whether ``native_runtime.demo.sh`` ran, and if not, the missing tool or policy
  reason;
* the generated files inspected for each template family;
* the generated README section used as the source for API names;
* the reference page that owns each option, template name, and config key;
* the first failure boundary for unknown template names, mutually exclusive
  template options, invalid custom config, rendering failure, and native build
  failure;
* confirmation that ordinary user prose uses ``--template`` for built-ins and
  reserves ``-t`` / ``--template-dir`` for trusted custom templates;
* confirmation that C-family statements are tied to the C runtime helper facts
  and not described as Python or all-platform behavior.
