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

End-to-end trace: one generation run
------------------------------------

This trace shows why generation failures should be diagnosed by layer instead of
by guessing at the final output file.

.. list-table:: Generation trace
   :header-rows: 1

   * - Step
     - Object or file
     - Owner
     - Failure class
   * - Read input bytes.
     - ``input.fcstm``.
     - CLI entry and decoder utilities.
     - File-not-found, unreadable bytes, or decoding failure.
   * - Parse DSL.
     - DSL AST nodes.
     - ``pyfcstm/dsl/``.
     - Grammar errors and source spans.
   * - Import model.
     - ``StateMachine``.
     - ``pyfcstm/model/`` and model importer code.
     - Model validation errors and semantic diagnostics.
   * - Resolve template source.
     - Extracted built-in directory or custom directory.
     - ``pyfcstm/template`` for built-ins, user project for custom templates.
     - Unknown built-in template, missing custom path, or broken package asset.
   * - Read template config.
     - ``config.yaml``.
     - Renderer validation.
     - Invalid YAML, wrong root type, invalid section shape, missing ``base_lang``.
   * - Build Jinja environment.
     - Globals, filters, tests, expression styles, statement styles.
     - Renderer plus trusted template config.
     - Helper import failure, invalid object-loading form, or missing style.
   * - Render/copy files.
     - Output tree.
     - Renderer and template files.
     - Jinja error, bad model attribute, filesystem write failure.
   * - Integrate target output.
     - Generated README, runtime source, consumer code, compiler.
     - Target-language user or template tests.
     - Runtime smoke failure, compiler error, unsupported deployment profile.

The key boundary is step 8. The renderer can prove that it produced files. It
cannot by itself prove that a target compiler, target event loop, or downstream
application integration is correct.

Built-in asset chain
--------------------

Built-in templates have a second chain before the normal renderer sees them:

.. list-table:: Built-in asset chain
   :header-rows: 1

   * - Stage
     - Source of truth
     - Reviewer question
   * - Repository source.
     - ``templates/<name>/`` and template README files.
     - Did the maintainer edit the source template, not a packaged zip by hand?
   * - Packaging.
     - ``tools/package_templates.py`` and ``make tpl``.
     - Did the packaged archive and ``pyfcstm/template/index.json`` refresh together?
   * - Package metadata.
     - ``pyfcstm/template/index.json``.
     - Does every documented template name, archive, root, language, and experimental flag match metadata?
   * - Extraction.
     - ``pyfcstm.template.extract_template()``.
     - Does ``--template`` produce an ordinary directory before rendering starts?
   * - Rendering.
     - ``StateMachineCodeRenderer``.
     - Does the extracted template follow the same ``config.yaml`` and file-mapping rules as a custom directory?

That split explains why user docs should prefer ``--template python`` while
maintainer docs may mention repository ``templates/`` source directories. The
ordinary generated-code user should not need to know where the source template
lives in a checkout.

Custom template trust boundary
------------------------------

A custom template is trusted code. Jinja sandboxing limits some template syntax,
but ``config.yaml`` can register imported Python objects through ``type:
import``. Therefore the safety boundary is not "arbitrary user uploads are safe".
The boundary is "the project running generation trusts this template directory".

.. list-table:: Trust-boundary examples
   :header-rows: 1

   * - Situation
     - Safe framing
     - Unsafe framing
   * - Team-owned template in the same repository.
     - Review it like source code and run renderer smoke checks.
     - Treat it as inert data because it is only a template.
   * - Third-party template directory.
     - Inspect ``config.yaml`` imports and Jinja files before running generation.
     - Run it in a privileged build environment without review.
   * - Environment-variable dependent template.
     - Document each variable as part of the project template contract.
     - Depend on undeclared developer shell state.

Renderer responsibility boundary
--------------------------------

The renderer owns structure, not every downstream promise. These examples are
useful when deciding where a bug belongs:

.. list-table:: Boundary examples
   :header-rows: 1

   * - Observed problem
     - Likely owner
     - Why
   * - ``*.j2`` file is rendered with the wrong output path.
     - Renderer file mapping or ignore rules.
     - The renderer decides suffix removal and static copy behavior.
   * - ``expr_render(style='go')`` emits unexpected expression syntax.
     - Expression renderer style implementation or style configuration.
     - The expression renderer owns expression textual shape.
   * - Generated C hook signature does not match generated README.
     - C template and generated README template.
     - Target API is emitted by the template, not by the generic renderer.
   * - Generated C code fails under a non-default embedded compiler.
     - Template target profile and downstream toolchain.
     - The renderer did not certify every compiler; it only emitted files.
   * - A custom imported helper performs hidden state transitions.
     - Custom template design.
     - Runtime semantics should be visible in generated source or target hooks.

Statement rendering design
--------------------------

Statement rendering exists because operation blocks are structured model nodes.
A renderer must know persistent variables, temporary variables, target assignment
syntax, and block syntax. A string echo cannot safely replace that context.

.. list-table:: Statement rendering context
   :header-rows: 1

   * - Context item
     - Why it matters
     - Example consequence
   * - Persistent state variables.
     - Assignments may need a state scope target.
     - Python runtime output uses ``scope[...]`` while C output uses a C struct pointer.
   * - Temporary variable names.
     - A variable assigned inside a block may be local after the first assignment.
     - The renderer must avoid treating every name as a persistent state variable.
   * - Temporary variable types.
     - Languages such as C need declaration text.
     - ``declare_temp`` and type aliases matter for executable output.
   * - Block structure.
     - ``if`` / ``elif`` / ``else`` syntax differs by language.
     - ``block_end`` is empty in Python-like indentation and explicit in brace languages.

This is why ``operation_stmt_render`` remains useful for DSL echo text but is not
a runtime-code shortcut.

Generated README as machine-specific evidence
---------------------------------------------

The generic pages cannot know every generated name because names are derived
from the model. The generated README is therefore part of the output contract.
Use this split when writing or reviewing docs:

* generic reference pages list template families, config keys, event-model
  shapes, and evidence boundaries;
* how-to pages show short commands and representative output snippets;
* the generated README lists the concrete machine class, C prefix, event ids,
  state ids, hook names, hot-start snippets, and build command for that model;
* tests and smoke demos prove selected generated README examples still execute.
