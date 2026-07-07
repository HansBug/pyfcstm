.. _sec-explanations-template-rendering:

Template rendering explanation
==============================

The renderer turns a validated state-machine model into a generated file tree.
It is intentionally a middle layer: it does not parse DSL text, it does not own
target-language runtime semantics, and it does not certify native deployment
profiles. Its job is to combine one ``StateMachine`` model with one trusted
template directory.

Two chains meet at generation time:

* the **user input chain**: FCSTM DSL text → AST → ``StateMachine`` model →
  renderer → generated files;
* the **template asset chain**: repository ``templates/`` source → packaging →
  ``pyfcstm/template/index.json`` and archives → extraction → renderer.

Those chains are separate on purpose. Built-in templates and custom templates
share the same ``StateMachineCodeRenderer`` once a normal template directory is
available, but they have different stability boundaries.

Rendering pipeline
------------------

The generation path is:

1. ``pyfcstm generate`` reads and decodes the FCSTM file.
2. The parser builds DSL AST nodes.
3. The model importer builds a validated ``StateMachine``.
4. For ``--template <name>``, ``pyfcstm.template.extract_template()`` extracts a
   packaged built-in template to a temporary directory.
5. For ``-t`` / ``--template-dir``, the user-supplied directory is used directly.
6. ``StateMachineCodeRenderer`` reads ``config.yaml``, validates the supported
   sections, and prepares a Jinja2 environment.
7. The renderer walks template files: ``*.j2`` files are rendered, other
   non-ignored files are copied, and ``config.yaml`` itself is skipped.
8. The generated directory is left for the target-language user to build,
   import, or inspect.

.. figure:: render_flow.puml.svg

   Rendering flow from DSL input to generated files.

Built-in and custom template boundary
-------------------------------------

A built-in template is a packaged asset. The stable user path is
``pyfcstm generate --template python`` or another listed built-in name. The
repository ``templates/`` directory is maintainer source, not the ordinary user
entry point.

A custom template is a trusted directory supplied through ``-t`` /
``--template-dir``. It can register imports, filters, and tests through
``config.yaml``. That makes it powerful enough for project-local code
generation, but it is not an untrusted-template sandbox.

.. figure:: architecture.puml.svg

   Renderer components and their responsibility boundaries.

Renderer responsibilities and non-responsibilities
--------------------------------------------------

.. list-table:: Responsibility boundary
   :header-rows: 1

   * - Area
     - Renderer owns
     - Template or target owns
   * - File tree
     - ``.j2`` rendering, static copy, ignores, directory creation.
     - Generated file names, target build layout, generated README wording.
   * - Configuration
     - Accepted ``config.yaml`` keys, validation, helper registration.
     - Which helpers are needed for a target runtime.
   * - Expressions and statements
     - Language-neutral renderers and style extension hooks.
     - The chosen target style, scope naming, temporary declarations.
   * - Runtime API
     - No target API decision.
     - Python class, C header API, C++ wrapper, polling callbacks.
   * - Evidence
     - Rendering success and source file mapping.
     - Formatter, compiler, runtime smoke, and simulator-alignment claims.

This separation keeps the renderer small and lets templates evolve target APIs
without turning the renderer into a cross-language runtime framework.

Jinja environment
-----------------

The base environment contains convenience filters and globals such as
``normalize``, ``to_identifier``, ``indent``, selected Python builtins,
``INIT_STATE``, and ``EXIT_STATE``. The renderer then adds ``expr_render``,
``stmt_render``, and ``stmts_render`` for the configured styles. A template may
also add ``globals``, ``filters``, and ``tests`` through ``config.yaml``.

C-family helper functions are deliberately registered by the C-family templates
through ``type: import``. They are not global defaults for every template. This
keeps C naming and C runtime body generation visible in each template's own
configuration.

Expression and statement rendering
----------------------------------

.. figure:: model.puml.svg

   Model objects provide language-neutral input consumed by templates.

Expressions are guards, assignment values, and other expression nodes. Operation
statements are assignment and ``if`` block structures inside lifecycle actions
and transition effects. Runtime templates should render them with the target
renderers:

.. code-block:: jinja

   {{ transition.guard | expr_render(style='c_scope_expr') }}
   {{ action.operations | stmts_render(style='c_runtime') }}

The older helpers have a different purpose:

.. list-table:: Statement helper choice
   :header-rows: 1

   * - Helper
     - Output intent
     - Correct use
   * - ``stmt_render`` / ``stmts_render``
     - Target-language executable statements.
     - Runtime source generation.
   * - ``operation_stmt_render`` / ``operation_stmts_render``
     - DSL echo text.
     - Comments, debug output, and documentation snippets.

A concrete counterexample: rendering ``counter = counter + 1;`` with
``operation_stmt_render`` produces DSL-like text. That is not the Python runtime
body shape that needs ``scope['counter']`` or the C runtime body shape that needs
``scope->counter``. Use the runtime statement renderer when generating code that
will execute.

Where logic should live
-----------------------

.. list-table:: Logic placement guide
   :header-rows: 1

   * - Logic type
     - Preferred home
     - Why
   * - Target runtime behavior
     - Generated source and target-language hooks.
     - Users can inspect and test the artifact they will ship.
   * - Repeated template structure
     - Jinja macros or includes.
     - Keeps layout reuse local to the template.
   * - Naming and formatting helpers
     - Template-local globals, filters, or tests.
     - Makes target conventions explicit in ``config.yaml``.
   * - Cross-template renderer behavior
     - Production renderer code plus tests.
     - Shared behavior needs normal API review.
   * - Maintainer-only process
     - Template maintainer README files and tooling checks.
     - Keeps user output focused on integration.

.. figure:: core_component.puml.svg

   Core renderer components and extension points.

Evidence boundary
-----------------

Generation documentation should name the evidence behind each claim:

.. list-table:: Evidence boundary
   :header-rows: 1

   * - Claim
     - Evidence
     - Do not overclaim
   * - Generation works
     - Command exits successfully and files exist.
     - Runtime behavior is not proven by file creation alone.
   * - Python output works
     - Generated class imports and a cycle smoke check runs.
     - Does not cover every semantic fixture.
   * - Native output compiles
     - A specific compiler / CMake smoke check succeeds.
     - Not all industrial or embedded compilers are certified.
   * - Simulator parity
     - Alignment tests compare traces with ``SimulationRuntime``.
     - Must state fixture coverage and target-specific exclusions.
   * - Formatter-friendly output
     - The relevant formatter accepts representative output.
     - Formatting must not override semantics or compatibility.

Generated README files are part of this evidence story. Reference pages provide
general contracts; generated README files provide the machine-specific API and
build facts for one generated model.
