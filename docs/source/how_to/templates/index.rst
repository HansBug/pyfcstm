.. _sec-how-to-templates:

Template author tasks
=====================

Use this guide when you are writing, debugging, or reviewing a custom template
directory. If you only want generated code, use :doc:`../generation/index` and a
packaged built-in template. If you need exact ``config.yaml`` facts, use
:doc:`../../reference/template_config/index`.

A custom template directory is trusted project code. ``type: import`` can load
Python objects available to the generator process, so do not render untrusted
template directories.

Create the smallest useful template
-----------------------------------

A template directory needs a ``config.yaml`` file and at least one output file.
Files ending in ``.j2`` are rendered through Jinja2; other non-ignored files are
copied as static assets.

.. code-block:: text

   my_template/
   ├── config.yaml
   ├── machine_summary.txt.j2
   └── static_note.txt

An empty configuration is legal. A first rendered file can inspect the model
object and state paths. This script writes the three files of the layout above
(``{}`` is the empty configuration) into the current directory:

.. testcode::

   from pathlib import Path

   template = Path("my_template")
   template.mkdir()
   (template / "config.yaml").write_text("{}\n")
   (template / "static_note.txt").write_text("Copied as is.\n")
   (template / "machine_summary.txt.j2").write_text("""\
   Machine: {{ model.root_state.name }}
   States:
   {%- for state in model.walk_states() %}
   - {{ state.path | join('.') }}
   {%- endfor %}
   """)

Download :download:`simple_machine.fcstm </_models/simple_machine.fcstm>`, the
tutorial model, into the same directory and render it:

.. code-block:: console

   $ pyfcstm generate -i simple_machine.fcstm -t my_template -o out --clear
   $ LC_ALL=C ls out
   machine_summary.txt
   static_note.txt
   $ cat out/machine_summary.txt
   Machine: SimpleMachine
   States:
   - SimpleMachine
   - SimpleMachine.Idle
   - SimpleMachine.Running
   - SimpleMachine.Stopped
   $ cat out/static_note.txt
   Copied as is.

The success signal is a generated ``machine_summary.txt`` plus the copied
``static_note.txt``. This proves only that the renderer can consume the
template; it does not prove target-language runtime semantics.

Understand file mapping
-----------------------

.. list-table:: File mapping rules
   :header-rows: 1

   * - Template source
     - Output behavior
     - Example
   * - ``*.j2``
     - Rendered with Jinja2 and written without the final ``.j2`` suffix.
     - ``src/machine.py.j2`` becomes ``src/machine.py``.
   * - Non-``.j2`` file
     - Copied byte-for-byte unless ignored or equal to ``config.yaml``.
     - ``LICENSE`` stays ``LICENSE``.
   * - ``config.yaml``
     - Read by the renderer and not copied to output.
     - Keep generator configuration out of generated user files.
   * - Ignored path
     - Excluded from rendering and copying.
     - ``ignores: ['README.md']`` keeps a maintainer README out of output.

The renderer always adds ``.git`` to the input-template ignore list. That does
not protect the output directory from ``--clear``; clearing is an output-side
operation.

Add expression and statement styles
-----------------------------------

Expressions and operation blocks are model objects, not target-language text.
A template chooses how to render them:

.. code-block:: yaml

   expr_styles:
     py_runtime_expr:
       base_lang: python
       Name: "scope[{{ node.name | tojson }}]"

   stmt_styles:
     py_runtime_stmt:
       base_lang: python
       expr_lang: python
       state_var_target: "scope[{{ name | tojson }}]"
       temp_var_target: "{{ name }}"

Use the filters in ``.j2`` files:

.. code-block:: jinja

   guard = {{ transition.guard | expr_render(style='py_runtime_expr') }}
   {{ action.operations | stmts_render(style='py_runtime_stmt') }}

Use ``stmt_render`` / ``stmts_render`` for executable runtime code. Use
``operation_stmt_render`` / ``operation_stmts_render`` only when you want a DSL
text echo for comments, documentation, or debugging. For example, a DSL effect
``counter = counter + 1;`` rendered through ``operation_stmt_render`` stays
DSL-like and is not valid Python assignment code for generated runtime bodies
that expect ``scope[...]`` accesses.

Register helpers through ``config.yaml``
------------------------------------------

``globals``, ``filters``, and ``tests`` share the same object-loading forms.
They let a template keep repeated naming and formatting logic out of long Jinja
expressions.

.. list-table:: Object-loading forms
   :header-rows: 1

   * - Form
     - Example
     - Result
   * - ``type: template`` with ``params``
     - ``params: [state]`` and ``template: "{{ state.path | join('.') }}"``
     - Returns a callable whose positional arguments are mapped to ``params``.
   * - ``type: template`` without ``params``
     - ``template: "{{ model.root_state.name }}"``
     - Returns the Jinja template's ``render`` callable.
   * - ``type: import``
     - ``from: pyfcstm.utils.to_c_identifier``
     - Imports a Python object for trusted template use.
   * - ``type: value``
     - ``value: 4``
     - Registers the literal value.
   * - No known ``type``
     - ``{prefix: Demo}``
     - Leaves the remaining mapping as the registered object.

C-family templates use explicit imports for helpers such as
``to_c_identifier``, ``to_c_path_identifier``, ``to_c_public_identifier``,
``render_c_action_body``, and ``render_c_condition_body``. Those helpers are not
injected into every renderer environment by default.

Keep target runtime behavior in generated code
----------------------------------------------

Template logic should be placed where reviewers can reason about it:

.. list-table:: Logic placement
   :header-rows: 1

   * - Logic type
     - Prefer this location
     - Reason
   * - Target runtime behavior
     - Generated target-language source and target-language hooks.
     - Users can inspect the output and run target-native checks.
   * - Repeated file structure
     - Jinja macros or includes.
     - Keeps templates readable without moving behavior into Python callbacks.
   * - Naming and formatting helpers
     - Template-local ``globals`` / ``filters`` / ``tests``.
     - Keeps conventions explicit in ``config.yaml``.
   * - Cross-template renderer behavior
     - Production code under ``pyfcstm/render/`` with tests.
     - Shared behavior needs normal Python review and regression coverage.
   * - Maintainer workflow rules
     - ``templates/README*.md`` and template tests.
     - They are not generated user output.

Validate a custom template
--------------------------

Use progressively stronger checks as your claims get stronger:

.. list-table:: Custom template validation matrix
   :header-rows: 1

   * - Layer
     - When needed
     - Success signal
     - Boundary
   * - Renderer smoke
     - Every custom template.
     - A small ``.fcstm`` renders, ``*.j2`` files appear, static files copy, ignores work.
     - Proves renderer compatibility only.
   * - Formatter
     - Generated target-language source is intended for users.
     - Representative output stabilizes under the target formatter.
     - Style quality gate, not semantics proof.
   * - Compiler / native smoke
     - Generated native source should compile.
     - Current toolchain configures, builds, and runs a small driver.
     - Toolchain-specific evidence only.
   * - Runtime smoke
     - Generated output exposes executable runtime behavior.
     - A minimal consumer constructs the machine and cycles it.
     - Does not cover all FCSTM semantics.
   * - Simulator alignment
     - The template claims parity with ``SimulationRuntime``.
     - Shared semantic fixtures or traces match the simulator.
     - Must state event-model exclusions and coverage.

Troubleshoot template authoring failures
----------------------------------------

.. list-table:: Template author troubleshooting
   :header-rows: 1

   * - Failure
     - What to inspect
     - Typical repair
   * - Unknown top-level key in ``config.yaml``
     - The exact key in the renderer error.
     - Move the value under one of ``expr_styles``, ``stmt_styles``, ``globals``, ``filters``, ``tests``, or ``ignores``.
   * - Style entry missing ``base_lang``
     - ``expr_styles.<name>`` or ``stmt_styles.<name>``.
     - Add a canonical base such as ``python`` or ``c``.
   * - Helper import fails
     - The ``from`` path and installed Python environment.
     - Use a public import path or keep the helper in project code available to generation.
   * - Static file unexpectedly copied
     - ``ignores`` patterns and path spelling.
     - Add a gitignore-style pattern; remember ``config.yaml`` is skipped separately.
   * - Output directory lost unrelated files
     - Use of ``--clear``.
     - Render into a scratch directory or omit ``--clear`` when preserving files matters.

Authoring task cards
--------------------

These cards turn the custom-template guide into reviewable tasks. Use them when
building a new template or when checking that a how-to example is not only a
fragment.

.. list-table:: Template author task cards
   :header-rows: 1

   * - Task
     - Input
     - Output or success signal
     - First troubleshooting step
   * - Render one text file.
     - ``config.yaml`` plus ``machine_summary.txt.j2``.
     - The output directory contains ``machine_summary.txt`` with the model name.
     - If the file is missing, confirm the source file really ends in ``.j2`` and is not ignored.
   * - Copy a static file.
     - A non-``.j2`` file such as ``static_note.txt``.
     - The same bytes appear in the output directory.
     - If it is copied unexpectedly, inspect ``ignores`` and remember ``config.yaml`` is skipped separately.
   * - Render a nested output path.
     - ``src/machine.py.j2`` or ``include/machine.h.j2``.
     - Parent directories are created and the final suffix is removed.
     - If the directory is absent, reduce to a single nested file before adding macros.
   * - Add a target expression style.
     - ``expr_styles.<name>.base_lang`` in ``config.yaml``.
     - ``{{ guard | expr_render(style='<name>') }}`` emits target syntax.
     - If validation rejects the style, check that the style value is a mapping with ``base_lang``.
   * - Add a target statement style.
     - ``stmt_styles.<name>.base_lang`` plus overrides such as ``assign``.
     - ``stmts_render`` emits executable assignment or ``if`` blocks for the target.
     - If output still looks like DSL, check that you did not call ``operation_stmt_render``.
   * - Register a filter.
     - ``filters.<name>: {type: import, from: package.module.object}``.
     - The template can call ``{{ value | name }}``.
     - If import fails, run the same import from Python in the generation environment.
   * - Register a value.
     - ``globals.project_name: {type: value, value: Demo}``.
     - ``{{ project_name }}`` renders the configured value.
     - If the value is a mapping instead, check whether ``type`` is missing or misspelled.
   * - Register a template callable.
     - ``type: template`` with optional ``params``.
     - Repeated formatting logic lives in a callable object instead of long inline Jinja.
     - If arguments bind incorrectly, test positional and keyword forms separately.
   * - Prove the template is not hiding runtime behavior.
     - Generated source plus a short consumer or compiler smoke.
     - The runtime behavior is visible in target-language output and hooks.
     - If behavior lives only in Python helper imports, move it into generated code or document why it is maintainer-only.

Minimal debug workflow
----------------------

When a custom template fails, debug in the same order as the renderer runs:

1. Validate the input FCSTM model with a normal command such as ``pyfcstm inspect``.
2. Validate ``config.yaml`` shape against :doc:`../../reference/template_config/index`.
3. Reduce to one ``*.j2`` file and one static file.
4. Add expression rendering, then statement rendering, then imported helpers.
5. Only after renderer smoke succeeds, run formatter, compiler, runtime, or alignment checks.

This order prevents a compiler error from hiding a renderer error, or a renderer
error from hiding an invalid model.

Runnable micro-template shape
-----------------------------

A short authoring example should fit on one screen. Keep the project-specific
logic out of the prose and name the success signal explicitly. This one declares a
named expression style, writes the model name and counts the states; it runs next to the template of
the first section:

.. testcode::

   from pathlib import Path

   template = Path("micro_template")
   template.mkdir()
   (template / "config.yaml").write_text("expr_styles:\n  py_expr:\n    base_lang: python\n")
   (template / "static_note.txt").write_text("Copied as is.\n")
   (template / "machine_summary.txt.j2").write_text("""\
   model={{ model.root_state.name }}
   states={{ model.walk_states() | list | length }}
   """)

.. code-block:: console

   $ pyfcstm generate -i simple_machine.fcstm -t micro_template -o micro_out --clear
   $ cat micro_out/machine_summary.txt
   model=SimpleMachine
   states=4

The success signal is a rendered ``machine_summary.txt`` and a copied
``static_note.txt``. This example proves file mapping and that the config file is read. It declares
a style but renders no expression, and it does not prove a generated runtime is
correct.

Helper design checklist
-----------------------

.. list-table:: Helper placement checklist
   :header-rows: 1

   * - Question
     - Good answer
     - Risky answer
   * - Is the helper pure naming or formatting?
     - Register it as a local filter or global and cover it with a renderer smoke.
     - Hide target runtime semantics in a Python helper that users cannot inspect.
   * - Does the helper emit C-family runtime bodies?
     - Reuse source facts from ``pyfcstm/render/c_runtime.py`` and document the target profile.
     - Reimplement C scope mutation in ad-hoc Jinja strings with no tests.
   * - Does the helper depend on host environment variables?
     - Treat it as project-specific and document the variable contract.
     - Depend on a developer's shell variable without a fallback.
   * - Does the helper cross multiple built-in templates?
     - Move shared behavior to reviewed renderer code with tests.
     - Copy divergent versions into several templates without a drift check.

Validation records to keep in a PR
----------------------------------

A template-authoring change should report these records when they apply:

* renderer smoke command and the generated files it produced;
* formatter command and the representative file it checked;
* compiler or native smoke command, or the exact missing tool reason;
* runtime smoke command and the observed output snippet;
* simulator-alignment command when parity is claimed;
* a short statement that ``operation_stmt_render`` was not used for executable
  runtime bodies.

Declare that a custom template supports regions
-----------------------------------------------

**Input.** A custom template directory and a model with regions
(:download:`controller.fcstm </_models/controller.fcstm>`, the interlock controller of
:doc:`/tutorials/regions/index`).  Download it, and the two files of
``region_listing_template/``, into an empty directory and run the commands
there.  A template is written for one execution
model.  ``features: [region]`` in ``config.yaml`` states that the template
renders models that declare regions.  Without the declaration, ``pyfcstm
generate`` refuses such a model before it writes anything; a model without
regions renders whatever the declaration says, so an existing template keeps
its output.  ``region_listing_template/`` is a minimal template that
declares the feature and lists every owner with its regions in writing order:

.. literalinclude:: region_listing_template/config.yaml
   :language: yaml
   :caption: region_listing_template/config.yaml

.. literalinclude:: region_listing_template/regions.txt.j2
   :language: jinja
   :caption: region_listing_template/regions.txt.j2

**Command or code.**

.. code-block:: console

   $ pyfcstm generate -i controller.fcstm -t region_listing_template -o out --clear
   $ cat out/regions.txt
   owner Controller.Running
     region 1: Safety (1 states)
     region 2: Motion (2 states)

.. testcode::

   from pyfcstm.render import StateMachineCodeRenderer

   renderer = StateMachineCodeRenderer("region_listing_template")
   print(sorted(renderer.features))

.. testoutput::

   ['region']

Without the declaration the same template is refused.  This is a negative
example:

.. code-block:: console

   $ mkdir undeclared
   $ cp region_listing_template/regions.txt.j2 undeclared/
   $ printf 'expr_styles: {}\n' > undeclared/config.yaml
   $ pyfcstm generate -i controller.fcstm -t undeclared -o undeclared_out --clear
   generate with template directory '.../undeclared' does not support region models yet. (line 12)
   The model declares 2 regions, the first is 'Controller.Running.Safety'.
   If you write this template: its config.yaml does not list `region` under `features`. List it (`features: [region]`) only once the template really renders regions, because a template written for a single active path would generate wrong code for them, which is why it is refused. See "Declaring model features" in templates/README.md.
   If you write the model: use a template that supports regions. Built-in templates that support regions: c, c_poll, cpp, cpp_poll, python.
     pyfcstm generate -i controller.fcstm --template c -o undeclared_out
   Or take the regions out of the model.
   $ echo $?
   1

The exit status is 1.  The tool prints the absolute path of the template
directory; it is left out as ``...`` here.

**Expected signal.** With the declaration, the output lists the owner and its
two regions in writing order, and ``StateMachineCodeRenderer.features`` is
``['region']``.  Without it, the message names the number of regions and the
first one, tells a template author what to declare and when, and lists the
built-in templates that support regions.

**What the template must satisfy once it declares** ``region``\ **.** The
declaration is a promise, not a switch.  The template takes over the region
semantics of its target language: an owner starts every region in writing
order, regions advance one after another within a cycle and see the writes of
the earlier ones, a region ends with ``-> [*]`` and then stays done, and the
last completion continues the owner in the same cycle or is refused.  A
template that claims this is expected to match
:class:`pyfcstm.simulate.SimulationRuntime` on every shared region scenario;
the built-in templates are the reference (see
:doc:`/reference/builtin_templates/index`).  Render regions through
``owner.regions`` and ``model.walk_regions()``, which keep writing order, and
do not declare ``region`` for a template that only walks a single path.
The listing template above is honest about this only because it does not
generate behavior.

**File side effect.** ``pyfcstm generate`` writes ``regions.txt`` into the
output directory; the commands write under ``out/``, ``undeclared/`` and
``undeclared_out/`` of the directory where you run them.

**First failure check.** If a template you changed is still refused, read
``StateMachineCodeRenderer(path).features``: an unknown or duplicated member of
``features`` fails when the renderer is constructed, and a template without the
key has an empty set.

**Reference link.** :doc:`/reference/template_config/index`.
