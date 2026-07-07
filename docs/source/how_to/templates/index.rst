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

An empty configuration is legal:

.. code-block:: yaml

   {}

A first rendered file can inspect the model object and state paths:

.. code-block:: jinja

   Machine: {{ model.name }}
   States:
   {%- for state in model.walk_states() %}
   - {{ state.path | join('.') }}
   {%- endfor %}

Render it with the tutorial model:

.. code-block:: bash

   pyfcstm generate \
       -i docs/source/tutorials/generation/simple_machine.fcstm \
       -t my_template \
       -o /tmp/pyfcstm-template-check \
       --clear

The expected success signal is a generated ``machine_summary.txt`` plus the
copied ``static_note.txt``. This proves only that the renderer can consume the
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
     - ``template: "{{ model.name }}"``
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
