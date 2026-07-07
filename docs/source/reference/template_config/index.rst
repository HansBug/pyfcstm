.. _sec-reference-template-config:

Template configuration reference
================================

This page is the lookup specification for template ``config.yaml`` files and
renderer-facing template directory behavior. Use it when maintaining a template
directory or diagnosing a rendering failure. For a task flow, see
:doc:`../../how_to/templates/index`; for design rationale, see
:doc:`../../explanations/template_rendering/index`.


.. template-config-marker: top-level-key expr_styles
.. template-config-marker: top-level-key stmt_styles
.. template-config-marker: top-level-key globals
.. template-config-marker: top-level-key filters
.. template-config-marker: top-level-key tests
.. template-config-marker: top-level-key ignores
.. template-config-marker: validation yaml-parse-error
.. template-config-marker: validation empty-file
.. template-config-marker: validation root-not-mapping
.. template-config-marker: validation unknown-top-level-key
.. template-config-marker: validation expr-styles-not-mapping
.. template-config-marker: validation stmt-styles-not-mapping
.. template-config-marker: validation globals-not-mapping
.. template-config-marker: validation filters-not-mapping
.. template-config-marker: validation tests-not-mapping
.. template-config-marker: validation expr-style-not-mapping
.. template-config-marker: validation expr-style-missing-base-lang
.. template-config-marker: validation stmt-style-not-mapping
.. template-config-marker: validation stmt-style-missing-base-lang
.. template-config-marker: validation ignores-not-list
.. template-config-marker: validation ignores-item-not-string
.. template-config-marker: validation object-template-missing-template
.. template-config-marker: validation object-import-missing-from
.. template-config-marker: validation object-value-missing-value
.. template-config-marker: validation object-import-target-failure
.. template-config-marker: style-name dsl
.. template-config-marker: style-name c
.. template-config-marker: style-name cpp
.. template-config-marker: style-name python
.. template-config-marker: style-name java
.. template-config-marker: style-name js
.. template-config-marker: style-name ts
.. template-config-marker: style-name rust
.. template-config-marker: style-name go
.. template-config-marker: style-alias py=python
.. template-config-marker: style-alias python3=python
.. template-config-marker: style-alias c++=cpp
.. template-config-marker: style-alias cxx=cpp
.. template-config-marker: style-alias cc=cpp
.. template-config-marker: style-alias javascript=js
.. template-config-marker: style-alias node=js
.. template-config-marker: style-alias nodejs=js
.. template-config-marker: style-alias typescript=ts
.. template-config-marker: style-alias rustlang=rust
.. template-config-marker: style-alias rs=rust
.. template-config-marker: style-alias golang=go
.. template-config-marker: stmt-field base_lang
.. template-config-marker: stmt-field expr_lang
.. template-config-marker: stmt-field expr_templates
.. template-config-marker: stmt-field state_var_target
.. template-config-marker: stmt-field temp_var_target
.. template-config-marker: stmt-field assign
.. template-config-marker: stmt-field declare_temp
.. template-config-marker: stmt-field temp_type_aliases
.. template-config-marker: stmt-field temp_type_fallback
.. template-config-marker: stmt-field if
.. template-config-marker: stmt-field elif
.. template-config-marker: stmt-field else
.. template-config-marker: stmt-field block_end
.. template-config-marker: stmt-field pass
.. template-config-marker: helper INIT_STATE
.. template-config-marker: helper EXIT_STATE
.. template-config-marker: helper expr_render
.. template-config-marker: helper stmt_render
.. template-config-marker: helper stmts_render
.. template-config-marker: helper _stmt_default_state_vars
.. template-config-marker: helper _stmt_default_var_types
.. template-config-marker: helper operation_stmt_render
.. template-config-marker: helper operation_stmts_render
.. template-config-marker: helper normalize
.. template-config-marker: helper to_identifier
.. template-config-marker: helper indent
.. template-config-marker: helper builtins
.. template-config-marker: helper environment-variables
.. template-config-marker: helper render_c_action_body
.. template-config-marker: helper render_c_condition_body
.. template-config-marker: helper render_c_reset_vars_body
.. template-config-marker: helper to_c_identifier
.. template-config-marker: helper to_c_path_identifier
.. template-config-marker: helper to_c_public_identifier
.. template-config-marker: helper to_c_public_macro_identifier
.. template-config-marker: helper is_c_public_identifier_reserved
.. template-config-marker: object-form template-with-params
.. template-config-marker: object-form template-without-params
.. template-config-marker: object-form import
.. template-config-marker: object-form value
.. template-config-marker: object-form unknown-type
.. template-config-marker: object-form no-type
.. template-config-marker: object-form non-dict
.. template-config-marker: file-mapping j2-render
.. template-config-marker: file-mapping static-copy
.. template-config-marker: file-mapping config-samefile-skip
.. template-config-marker: file-mapping git-ignore-input-only
.. template-config-marker: file-mapping ignores-gitwildmatch
.. template-config-marker: file-mapping nested-output-dirs
.. template-config-marker: file-mapping utf8-lf-render
.. template-config-marker: file-mapping static-copy-bytes
.. template-config-marker: file-mapping clear-symlink-unlink
.. template-config-marker: file-mapping clear-file-remove
.. template-config-marker: file-mapping clear-directory-rmtree
.. template-config-marker: file-mapping clear-other-warning

File contract
-------------

A template directory may contain ``config.yaml``. The renderer reads it before
walking files. Empty files and comment-only files are treated as an empty
mapping. When no ``expr_styles.default`` or ``stmt_styles.default`` is supplied,
the renderer creates a default DSL style.

Only these top-level keys are accepted:

.. list-table:: ``config.yaml`` top-level keys
   :header-rows: 1

   * - Key
     - Type
     - Meaning
   * - ``expr_styles``
     - mapping
     - Registers expression rendering styles used by ``expr_render``.
   * - ``stmt_styles``
     - mapping
     - Registers operation-statement rendering styles used by ``stmt_render`` and ``stmts_render``.
   * - ``globals``
     - mapping
     - Adds Jinja2 globals through ``process_item_to_object``.
   * - ``filters``
     - mapping
     - Adds Jinja2 filters through the same object-loading mechanism.
   * - ``tests``
     - mapping
     - Adds Jinja2 tests through the same object-loading mechanism.
   * - ``ignores``
     - list of strings
     - GitWildMatch-style patterns for input template files that should not be rendered or copied.

Validation failures
-------------------

The renderer fails fast on invalid configuration. The message includes the
configuration file path and the failing key shape where available.

.. list-table:: Validation branches
   :header-rows: 1

   * - Marker
     - Invalid shape
     - Minimal counterexample
   * - ``yaml-parse-error``
     - YAML syntax cannot be parsed.
     - ``expr_styles: [``
   * - ``empty-file``
     - Empty or comment-only file.
     - Accepted as ``{}``; not a failure.
   * - ``root-not-mapping``
     - Root value is not a mapping.
     - ``[]``
   * - ``unknown-top-level-key``
     - Root has a key outside the accepted set.
     - ``unknown: true``
   * - ``expr-styles-not-mapping``
     - ``expr_styles`` is not a mapping.
     - ``expr_styles: []``
   * - ``stmt-styles-not-mapping``
     - ``stmt_styles`` is not a mapping.
     - ``stmt_styles: []``
   * - ``globals-not-mapping``
     - ``globals`` is not a mapping.
     - ``globals: []``
   * - ``filters-not-mapping``
     - ``filters`` is not a mapping.
     - ``filters: []``
   * - ``tests-not-mapping``
     - ``tests`` is not a mapping.
     - ``tests: []``
   * - ``expr-style-not-mapping``
     - One expression style entry is not a mapping.
     - ``expr_styles: {py: python}``
   * - ``expr-style-missing-base-lang``
     - One expression style lacks ``base_lang``.
     - ``expr_styles: {py: {Name: x}}``
   * - ``stmt-style-not-mapping``
     - One statement style entry is not a mapping.
     - ``stmt_styles: {py: python}``
   * - ``stmt-style-missing-base-lang``
     - One statement style lacks ``base_lang``.
     - ``stmt_styles: {py: {assign: x}}``
   * - ``ignores-not-list``
     - ``ignores`` is a string or other non-list value.
     - ``ignores: '*.tmp'``
   * - ``ignores-item-not-string``
     - One ignore item is not a string.
     - ``ignores: [123]``

Object-loading failures happen when the selected form is incomplete or cannot
be imported:

.. list-table:: Object-loading failure shapes
   :header-rows: 1

   * - Marker
     - Invalid shape
     - Effect
   * - ``object-template-missing-template``
     - ``type: template`` without ``template``.
     - ``KeyError`` from the loader.
   * - ``object-import-missing-from``
     - ``type: import`` without ``from``.
     - ``KeyError`` from the loader.
   * - ``object-value-missing-value``
     - ``type: value`` without ``value``.
     - ``KeyError`` from the loader.
   * - ``object-import-target-failure``
     - ``from`` points to an unavailable object.
     - Import failure from ``quick_import_object``.

Expression styles
-----------------

An expression style maps a template-local style name to a canonical expression
renderer. Every style entry must contain ``base_lang``. Extra keys override or
extend node templates for that style.

.. code-block:: yaml

   expr_styles:
     c_scope_expr:
       base_lang: c
       Name: "scope->{{ node.name | to_c_identifier }}"

Use it from templates:

.. code-block:: jinja

   {{ transition.guard | expr_render(style='c_scope_expr') }}

Canonical style names and aliases are exact:

.. list-table:: Style names and aliases
   :header-rows: 1

   * - Canonical
     - Aliases
   * - ``dsl``
     - none
   * - ``c``
     - none
   * - ``cpp``
     - ``c++``, ``cxx``, ``cc``
   * - ``python``
     - ``py``, ``python3``
   * - ``java``
     - none
   * - ``js``
     - ``javascript``, ``node``, ``nodejs``
   * - ``ts``
     - ``typescript``
   * - ``rust``
     - ``rustlang``, ``rs``
   * - ``go``
     - ``golang``

Statement styles
----------------

A statement style renders assignments and ``if`` blocks in operation blocks. It
has the same ``base_lang`` requirement and may also set these fields:

.. list-table:: ``stmt_styles`` fields
   :header-rows: 1

   * - Field
     - Meaning
   * - ``base_lang``
     - Canonical statement language to start from.
   * - ``expr_lang``
     - Expression renderer used inside statements.
   * - ``expr_templates``
     - Expression template overrides scoped to statement rendering.
   * - ``state_var_target``
     - Jinja template for persistent variable writes and reads.
   * - ``temp_var_target``
     - Jinja template for block-local temporary names.
   * - ``assign``
     - Assignment statement template.
   * - ``declare_temp``
     - Optional declaration emitted when a temporary first appears.
   * - ``temp_type_aliases``
     - Mapping from inferred DSL types such as ``int`` / ``float`` to target types.
   * - ``temp_type_fallback``
     - Fallback type when inference cannot decide.
   * - ``if`` / ``elif`` / ``else`` / ``block_end`` / ``pass``
     - Control-flow templates for conditional blocks and empty branches.

The renderer provides these helper signatures:

.. code-block:: text

   stmt_render(node, style='default', state_vars=None, var_types=None,
               visible_names=None, visible_var_types=None,
               indent='    ', level=0)

   stmts_render(nodes, style='default', state_vars=None, var_types=None,
                visible_names=None, visible_var_types=None,
                indent='    ', level=0, sep='\n')

``state_vars`` and ``var_types`` default to renderer-injected model variables
when a full ``StateMachine`` render is active. ``visible_names`` and
``visible_var_types`` describe temporary variables already visible to the
statement renderer. ``sep`` controls how rendered statement strings are joined:

.. code-block:: jinja

   {{ action.operations | stmts_render(style='python_runtime', sep='\n') }}

Runtime statement renderer vs DSL echo renderer
-----------------------------------------------

.. list-table:: Statement helper distinction
   :header-rows: 1

   * - Helper
     - Contract
     - Do not use for
   * - ``stmt_render`` / ``stmts_render``
     - Render executable target-language statements.
     - Raw DSL echo snippets.
   * - ``operation_stmt_render`` / ``operation_stmts_render``
     - Render DSL-like text from operation statements.
     - Runtime source code that must execute in Python, C, or another target.

Counterexample: a DSL effect ``counter = counter + 1;`` rendered with
``operation_stmt_render`` remains ``counter = counter + 1;``. A Python runtime
style may need ``scope['counter'] = scope['counter'] + 1``; a C runtime style
may need ``scope->counter = scope->counter + 1;``.

Object-loading forms
--------------------

``globals``, ``filters``, and ``tests`` all pass values through
``process_item_to_object``.

.. list-table:: Object-loading forms
   :header-rows: 1

   * - Form
     - YAML shape
     - Registered object
   * - ``template-with-params``
     - ``type: template`` plus ``params`` and ``template``.
     - Callable mapping positional args to ``params`` and merging kwargs.
   * - ``template-without-params``
     - ``type: template`` plus ``template`` only.
     - Jinja template ``render`` callable.
   * - ``import``
     - ``type: import`` plus ``from``.
     - Imported Python object.
   * - ``value``
     - ``type: value`` plus ``value``.
     - Literal value.
   * - ``unknown-type`` / ``no-type``
     - A mapping with an unrecognized or missing ``type``.
     - Remaining mapping after ``type`` is popped, or the original mapping.
   * - ``non-dict``
     - Any non-mapping value under a config section, including scalars, lists, and ``null``.
     - Returned unchanged.

C-family templates use ``type: import`` for ``render_c_action_body``,
``render_c_condition_body``, ``render_c_reset_vars_body``, ``to_c_identifier``,
``to_c_path_identifier``, ``to_c_public_identifier``,
``to_c_public_macro_identifier``, and ``is_c_public_identifier_reserved``.

Jinja environment helpers
-------------------------

The default environment includes:

* state constants: ``INIT_STATE`` and ``EXIT_STATE``;
* render helpers: ``expr_render``, ``stmt_render``, ``stmts_render``,
  ``operation_stmt_render``, and ``operation_stmts_render``;
* text helpers: ``normalize``, ``to_identifier``, and ``indent``;
  ``normalize`` uses ``unidecode`` to transliterate Unicode text before
  identifier cleanup, so templates that accept non-ASCII machine names should
  test their emitted identifiers;
* render-time statement defaults: ``_stmt_default_state_vars`` and
  ``_stmt_default_var_types`` are injected only while rendering a full
  ``StateMachine`` and supply default persistent variable names and types for
  ``stmt_render`` / ``stmts_render`` when their ``state_vars`` / ``var_types``
  arguments are omitted;
* common Python builtins registered as filters, tests, or globals, including
  ``str``, ``set``, ``dict``, ``keys``, ``values``, ``enumerate``, ``reversed``,
  and ``filter``;
* operating-system environment variables from ``os.environ`` as globals when
  their names do not conflict with existing Jinja globals.

Environment variables are a convenience for controlled build environments. They
are not a secret boundary: a trusted template can read any non-conflicting
process environment variable visible to the generator process. A portable
template should not depend on host-specific values unless that contract is
documented by the project using the custom template.

File mapping, ignore, and clear semantics
-----------------------------------------

.. list-table:: Renderer file behavior
   :header-rows: 1

   * - Behavior
     - Contract
   * - ``j2-render``
     - ``*.j2`` files render to the same relative path without the final suffix.
   * - ``static-copy``
     - Non-template files copy with ``shutil.copyfile`` and preserve bytes.
   * - ``config-samefile-skip``
     - ``config.yaml`` is skipped by ``os.path.samefile(current_file, self.config_file)``.
   * - ``git-ignore-input-only``
     - ``.git`` is always ignored while scanning template input.
   * - ``ignores-gitwildmatch``
     - ``ignores`` uses GitWildMatch-style patterns through ``pathspec``.
   * - ``nested-output-dirs``
     - Parent directories are created for nested output paths.
   * - ``utf8-lf-render``
     - Rendered text is written as UTF-8 with ``newline='\n'``.
   * - ``static-copy-bytes``
     - Static assets are copied byte-for-byte.
   * - ``clear-symlink-unlink`` / ``clear-file-remove`` / ``clear-directory-rmtree``
     - Output clearing unlinks symlinks, removes files, and recursively deletes directories.
   * - ``clear-other-warning``
     - Other file types produce a defensive warning path.

``.git`` input ignoring does not protect an output directory. If ``--clear`` is
pointed at a working tree, the renderer follows output clearing rules for that
directory.

Built-in config examples
------------------------

The built-in templates exercise the same contract:

* ``python`` defines Python expression and statement styles and generated hook
  naming helpers.
* ``c`` and ``c_poll`` define C scope expression rendering, C runtime statement
  rendering, C identifier filters, and C runtime body helpers.
* ``cpp`` and ``cpp_poll`` reuse the C-family helper layer while adding wrapper
  files; their ``ignores`` list also names ``config.yaml`` redundantly, which is
  harmless because the renderer already skips the actual config file.
