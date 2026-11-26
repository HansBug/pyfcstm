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

.. literalinclude:: /_models/simple_machine.fcstm
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

A minimal Python consumer imports ``machine.py``.

The smoke check below uses the interlock controller of the regions tutorial; download :download:`controller.fcstm </_models/controller.fcstm>` into an empty directory. The generated ``machine.py`` does not depend on ``pyfcstm``, so a plain ``python`` can import it:

.. code-block:: console

   $ pyfcstm generate -i controller.fcstm --template python -o generated/python --clear
   $ PYTHONPATH=generated/python python -c "import machine; print(machine.ControllerMachine.__name__)"
   ControllerMachine

This evidence means the generated Python runtime is importable. A consumer that
sends events and reads the position is the program of the first card in
`Tasks for models with regions`_. Broader simulator alignment is covered by
template unit tests, not by this smoke check.

Smoke-check C and C++ outputs
-----------------------------

The native check needs a C compiler, and the C++ templates also need a C++
compiler and ``cmake``, so the documentation checks do not run it. The card
`Set the capacity macros of the C runtime`_ builds the generated ``c`` runtime
with a small driver; it shows the commands and the output recorded from one
build.

That card is a local smoke check. It proves that the generated files compiled and
ran on the toolchain that built it. It is not a claim that every embedded compiler,
industrial profile, sanitizer profile, or certification environment has been
validated.

When a native smoke check fails, record the compiler and ``cmake`` versions first, then
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
     - ``pyfcstm generate -i docs/source/_models/simple_machine.fcstm --template python -o /tmp/pyfcstm-python --clear``
     - ``machine.py`` and generated README files exist; the README names the concrete class.
     - ``--clear`` replaces the scratch output. If it fails, confirm the input parses before inspecting the template.
   * - Generate explicit-event C output.
     - ``pyfcstm generate -i docs/source/_models/simple_machine.fcstm --template c -o /tmp/pyfcstm-c --clear``
     - ``machine.h`` and ``machine.c`` exist, and the README shows event ids.
     - A later compiler smoke must use the generated header. If event names are unclear, read the generated README rather than guessing ids.
   * - Generate polling C output.
     - ``pyfcstm generate -i docs/source/_models/simple_machine.fcstm --template c_poll -o /tmp/pyfcstm-c-poll --clear``
     - ``machine.h`` documents the event-check table shape.
     - Polling requires callbacks for event truth. If events never fire, inspect ``EventChecks`` before editing state-machine logic.
   * - Generate the C++ wrapper.
     - ``pyfcstm generate -i docs/source/_models/simple_machine.fcstm --template cpp -o /tmp/pyfcstm-cpp --clear``
     - ``machine.hpp`` and ``machine.cpp`` appear in addition to the C core.
     - User code should include ``machine.hpp``. If a build bypasses the wrapper, the smoke no longer proves the documented C++ surface.
   * - Generate the C++ polling wrapper.
     - ``pyfcstm generate -i docs/source/_models/simple_machine.fcstm --template cpp_poll -o /tmp/pyfcstm-cpp-poll --clear``
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

The small native smoke for this page is the compile-and-run driver of the
capacity card; the repository's native-toolchain template tests are the larger
one (``PYFCSTM_RUN_NATIVE_TOOLCHAIN=1 make template_unittest
TEMPLATE_UNITTEST_ARGS="--include-suites c --run-native-toolchain"``). A PR that
changes generation, C-family template docs, or native claims should either run
one of them or state the exact reason it could not run in that environment.

When it runs, record the compiler versions and the per-template result.
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
* whether a native compile-and-run smoke ran, and if not, the missing tool or policy
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

Tasks for models with regions
-----------------------------

Every built-in template (``python``, ``c``, ``c_poll``, ``cpp`` and
``cpp_poll``) generates a runtime for a model with regions.  The cards below
use the interlock controller of
:doc:`/tutorials/regions/index` (:download:`controller.fcstm </_models/controller.fcstm>`), and state the same six facts: **Input**,
**Command or code**, **Expected signal**, **File side effect**, **First
failure check** and **Reference link**.  The generated runtimes match
:class:`pyfcstm.simulate.SimulationRuntime` cycle by cycle; the modeling tasks
are on :doc:`/how_to/regions/index`.

Generate the five runtimes and run the Python one
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Input.** ``controller.fcstm`` and a Python 3.7+ interpreter.  The
generated ``machine.py`` has no dependency on ``pyfcstm``.  Download
:download:`region_app.py` next to it.  The program
``region_app.py`` subclasses the generated class, implements the two input
readers, and reads the position through ``configuration``, ``leaves``,
``is_active`` and ``region_status``; it also restores a hot start and sends
events.

.. literalinclude:: region_app.py
   :language: python
   :caption: region_app.py

**Command or code.**

.. code-block:: console

   $ pyfcstm generate -i controller.fcstm --template python -o out/python --clear
   $ pyfcstm generate -i controller.fcstm --template c -o out/c --clear
   $ pyfcstm generate -i controller.fcstm --template c_poll -o out/c_poll --clear
   $ pyfcstm generate -i controller.fcstm --template cpp -o out/cpp --clear
   $ pyfcstm generate -i controller.fcstm --template cpp_poll -o out/cpp_poll --clear
   $ LC_ALL=C ls out/*
   out/c:
   README.md
   README_zh.md
   machine.c
   machine.h

   out/c_poll:
   README.md
   README_zh.md
   machine.c
   machine.h

   out/cpp:
   README.md
   README_zh.md
   machine.c
   machine.cpp
   machine.h
   machine.hpp

   out/cpp_poll:
   README.md
   README_zh.md
   machine.c
   machine.cpp
   machine.h
   machine.hpp

   out/python:
   README.md
   README_zh.md
   machine.py
   $ PYTHONPATH=out/python python region_app.py
   after start: Controller.Running{Safety: Watching, Motion: On}
     leaves ['Controller.Running.Safety.Watching', 'Controller.Running.Motion.On']
     motor=1 permit=1
   is_active Running: True
   region_status Safety: live
   fault raised: Controller.Running{Safety: Watching, Motion: Off}
     leaves ['Controller.Running.Safety.Watching', 'Controller.Running.Motion.Off']
     motor=0 permit=0
   hot start: Controller.Running{Safety: Watching, Motion: On}
     leaves ['Controller.Running.Safety.Watching', 'Controller.Running.Motion.On']
     motor=1 permit=1
   hot start, one cycle later: Controller.Running{Safety: Watching, Motion: Off}
     leaves ['Controller.Running.Safety.Watching', 'Controller.Running.Motion.Off']
     motor=0 permit=0
   after /Stop: Controller.Idle
     leaves ['Controller.Idle']
     motor=0 permit=0
**Expected signal.** The listing shows the generated files of each
template.  The program prints the position as text
(``Controller.Running{Safety: Watching, Motion: On}``), the active leaves, and
the variables.  A raised ``fault`` turns the motor off in the same cycle.
The hot start places both regions without any ``enter`` action, and
``initial_vars`` carries the hidden variable ``__forced_0`` like any other.
The ``/Stop`` event leaves ``Running`` in one cycle.

**File side effect.** ``pyfcstm generate`` writes the files above into the
output directory and, with ``--clear``, empties it first.  The commands write
under ``out/`` in the directory where you run them.

**First failure check.** If the program raises ``SimulationRuntimeEventError``,
read the message: a name that depends on the position is resolved once for
every active leaf, so use the full path or ``/Name``.  If a class name or
method is not what you expected, read the generated ``README.md``: it is
written for this model.

**Reference link.** :doc:`/reference/builtin_templates/index`.

Set the capacity macros of the C runtime
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Input.** The ``c`` runtime of the same model, a C compiler, and
:download:`region_capacity_app.c`.  The machine reserves its storage statically; two
macros in ``machine.h`` size it:
``CONTROLLER_MACHINE_ARENA_CAPACITY`` (configurations and work items examined
by one decision) and ``CONTROLLER_MACHINE_TRAIL_CAPACITY`` (nested checks).
The defaults are computed from the model.  Override them only if a cycle
fails with the capacity message.  Define an overridden value identically for
``machine.c`` and every file that includes ``machine.h``.

.. literalinclude:: region_capacity_app.c
   :language: c
   :caption: region_capacity_app.c

**Command or code.** The commands build the program three times: with the
defaults, with a value that is too small (to show the failure), and with larger
values.  They need a C compiler, so the documentation checks do not run them;
the output below was recorded from a real run of exactly these commands:

.. code-block:: bash

   pyfcstm generate -i controller.fcstm --template c -o c_out --clear
   cp region_capacity_app.c c_out/app.c
   grep -E '^#define CONTROLLER_MACHINE_(ARENA|TRAIL)_CAPACITY' c_out/machine.h
   cd c_out
   cc -std=c99 -Wall -Wextra -pedantic -O2 machine.c app.c -lm -o app && ./app
   cc -std=c99 -Wall -Wextra -pedantic -O2 -DCONTROLLER_MACHINE_ARENA_CAPACITY=4 machine.c app.c -lm -o app && ./app
   cc -std=c99 -Wall -Wextra -pedantic -O2 -DCONTROLLER_MACHINE_ARENA_CAPACITY=480 -DCONTROLLER_MACHINE_TRAIL_CAPACITY=96 machine.c app.c -lm -o app && ./app

.. code-block:: text

   #define CONTROLLER_MACHINE_ARENA_CAPACITY 108
   #define CONTROLLER_MACHINE_TRAIL_CAPACITY 52
   storage bytes: 14272
   cycle 1: Controller.Idle motor=0
   cycle 2: Controller.Running{Safety: Watching, Motion: Off} motor=0
   cycle 3: Controller.Running{Safety: Watching, Motion: On} motor=1
   storage bytes: 3040
   cycle 1: Controller.Idle motor=0
   cycle 2 failed: Speculative search exceeded the capacity safety limit (4 configurations); define CONTROLLER_MACHINE_ARENA_CAPACITY to a larger value to allow a longer search.
   storage bytes: 55856
   cycle 1: Controller.Idle motor=0
   cycle 2: Controller.Running{Safety: Watching, Motion: Off} motor=0
   cycle 3: Controller.Running{Safety: Watching, Motion: On} motor=1

**Expected signal.** The defaults suffice: three cycles, exit status 0.  With
``ARENA_CAPACITY=4`` cycle 2 (the one that enters the regions) fails with
``Speculative search exceeded the capacity safety limit`` and the message names
the macro; the machine reports the failure instead of misbehaving.  Larger
values also succeed and make the storage bigger (``storage bytes``).  To confirm
that a chosen value is enough, run the scenarios you care about with it: a value
that is too small fails loudly, so a clean run is the evidence.  Storage size is
platform dependent (the numbers above come from one 64-bit build).

**File side effect.** The commands write the generated sources and the binary
to ``c_out/``.

**First failure check.** Read the failure message: it names the macro to raise.
If the program fails only in some builds, check that every translation unit
sees the same ``-D`` value.

**Reference link.** :doc:`/reference/builtin_templates/index`.

Handle a template that does not declare ``region``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Input.** :download:`plain_template/config.yaml` and :download:`plain_template/summary.txt.j2` in a directory ``plain_template/``, a custom template whose ``config.yaml`` does
not list ``region`` under ``features``, and a model with regions.  A template
written for one active path would produce wrong code for regions, so
``pyfcstm generate`` refuses before it writes anything.  This is a negative
example.

**Command or code.**

.. code-block:: console

   $ pyfcstm generate -i controller.fcstm -t plain_template -o refused_out --clear
   generate with template directory '.../plain_template' does not support region models yet. (line 12)
   The model declares 2 regions, the first is 'Controller.Running.Safety'.
   If you write this template: its config.yaml does not list `region` under `features`. List it (`features: [region]`) only once the template really renders regions, because a template written for a single active path would generate wrong code for them, which is why it is refused. See "Declaring model features" in templates/README.md.
   If you write the model: use a template that supports regions. Built-in templates that support regions: c, c_poll, cpp, cpp_poll, python.
     pyfcstm generate -i controller.fcstm --template c -o refused_out
   Or take the regions out of the model.
   $ echo $?
   1
   $ test ! -e refused_out && echo "no output directory was written"
   no output directory was written
   $ pyfcstm generate -i controller.fcstm --template python -o refused_out --clear
   $ LC_ALL=C ls refused_out
   README.md
   README_zh.md
   machine.py

The exit status is 1.  The tool prints the absolute path of the template
directory; it is left out as ``...`` here.

**Expected signal.** The message names the first region, and gives two ways
out: if you write the template, declare ``features: [region]`` only after the
template really renders regions (see :doc:`/how_to/templates/index`); if you
write the model, use a template that supports regions.  Using a built-in
template succeeds (the last two commands above).

**File side effect.** None on failure: no output directory is created.

**First failure check.** Read the line that starts ``If you write this
template`` or ``If you write the model`` and take the branch that applies.

**Reference link.** :doc:`/reference/template_config/index`.
