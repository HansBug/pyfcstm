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
.. template-config-marker: top-level-key features
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
.. template-config-marker: validation features-not-list
.. template-config-marker: validation features-item-not-string
.. template-config-marker: validation features-unknown-feature
.. template-config-marker: validation features-duplicate-feature
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

A template directory must contain ``config.yaml``. The renderer reads it
before walking files; a missing file fails before any template file is rendered.
Empty files and comment-only files are treated as an empty mapping. When no
``expr_styles.default`` or ``stmt_styles.default`` is supplied, the renderer
creates a default DSL style.

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
   * - ``features``
     - list of strings
     - Model features the template can render. The only member is ``region``; see :ref:`sec-reference-template-config-features`.

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
   * - ``features-not-list``
     - ``features`` is a string, a mapping or another non-list value (``null`` is not a failure, see below).
     - ``features: region``
   * - ``features-item-not-string``
     - One ``features`` item is not a string.
     - ``features: [1]``
   * - ``features-unknown-feature``
     - One ``features`` item is not a supported feature name; names are case-sensitive.
     - ``features: [cloud]``
   * - ``features-duplicate-feature``
     - The same feature is listed twice.
     - ``features: [region, region]``

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

.. _sec-reference-template-config-features:

Declaring model features
------------------------

``features`` is how a template says which model constructs it can render. A
template that does not declare a feature is refused for any model that needs it,
before a file is written. Today the closed list has one member.

.. list-table:: ``features`` contract
   :header-rows: 1

   * - Item
     - Fact
   * - Spelling
     - Top-level key ``features`` in ``config.yaml``.
   * - Type
     - List of strings. An absent key, ``features:`` (``null``) and ``features: []`` all mean "nothing declared".
   * - Allowed members
     - ``region`` only (``_TEMPLATE_FEATURES`` in ``pyfcstm/render/render.py``). Matching is exact, so ``Region`` is rejected.
   * - Default
     - Nothing declared. A template written before regions existed therefore refuses every model that declares a region.
   * - Meaning of ``region``
     - The template renders models that declare ``region`` blocks, including nested ones. Declare it only when the template really does; a template written for one active path would generate wrong code for a model with regions.
   * - Needed by
     - Only a model that declares at least one region. A model without regions renders with or without the declaration.
   * - Read back
     - ``StateMachineCodeRenderer(template_dir).features`` returns a ``frozenset`` of the declared names.
   * - Checked by
     - ``StateMachineCodeRenderer.render`` and ``render_one_file``, before the output directory is created or cleared, and by ``pyfcstm generate`` before it calls the renderer.
   * - Built-in templates
     - ``python``, ``c``, ``c_poll``, ``cpp`` and ``cpp_poll`` all declare ``features: [region]`` in their ``config.yaml``.

Legal declarations:

.. list-table:: ``features`` examples
   :header-rows: 1

   * - Case
     - YAML
     - Result
   * - Renders regions.
     - ``features: [region]``
     - Legal. A model with regions is accepted.
   * - No declaration.
     - key absent, or ``{}``
     - Legal. A model with regions is refused; a model without regions renders.
   * - Explicit empty list.
     - ``features: []``
     - Legal and equivalent to leaving the key out.
   * - Empty value.
     - ``features:``
     - Legal. YAML reads it as ``null``, which counts as nothing declared.
   * - String instead of list.
     - ``features: region``
     - Invalid. Write ``features: [region]``.
   * - Mapping.
     - ``features: {region: true}``
     - Invalid. The value must be a list.
   * - Unknown or differently cased name.
     - ``features: [cloud]``, ``features: [Region]``
     - Invalid. Only ``region`` exists.
   * - Repeated name.
     - ``features: [region, region]``
     - Invalid.
   * - Non-string item.
     - ``features: [1]``, ``features: [null]``
     - Invalid.

The validation errors are ``ValueError`` raised when the renderer reads the
configuration. Each of them names the configuration file; ``...`` below stands
for the temporary directory of the script. The script builds the renderer once
for each one-line ``config.yaml``:

.. testcode::

   import tempfile
   from pathlib import Path

   from pyfcstm.render import StateMachineCodeRenderer

   configs = ("{}", "features: [region]", "features: []", "features:", "features: region",
              "features: {region: true}", "features: [cloud]", "features: [Region]",
              "features: [region, region]", "features: [1]", "features: [null]")
   for text in configs:
       with tempfile.TemporaryDirectory() as work:
           Path(work, "config.yaml").write_text(text + "\n")
           try:
               print(text, "->", sorted(StateMachineCodeRenderer(work).features))
           except ValueError as err:
               print(text, "-> ValueError:", err)

.. testoutput::

   {} -> []
   features: [region] -> ['region']
   features: [] -> []
   features: -> []
   features: region -> ValueError: Renderer config .../config.yaml top-level key 'features' must be a list of feature names, got str.
   features: {region: true} -> ValueError: Renderer config .../config.yaml top-level key 'features' must be a list of feature names, got dict.
   features: [cloud] -> ValueError: Renderer config .../config.yaml declares unknown feature 'cloud'. Supported features: region.
   features: [Region] -> ValueError: Renderer config .../config.yaml declares unknown feature 'Region'. Supported features: region.
   features: [region, region] -> ValueError: Renderer config .../config.yaml declares duplicate feature 'region'.
   features: [1] -> ValueError: Renderer config .../config.yaml features[0] must be a string, got int.
   features: [null] -> ValueError: Renderer config .../config.yaml features[0] must be a string, got NoneType.

The key is also checked by ``pyfcstm generate``. The next commands build four
template directories and render ``controller.fcstm`` (two regions) or
``region_plain.fcstm`` (none) into each one. A refused run exits with status 1,
writes nothing, and prints the model's region count, where the first region is,
what a template author should declare, which built-in templates to use instead,
and one command that can be copied. The suggested template is the first name of
the printed list. The ``(line 12)`` is the line of the first region
in ``controller.fcstm``.

.. literalinclude:: /_models/controller.fcstm
   :language: fcstm
   :caption: controller.fcstm

.. literalinclude:: region_plain.fcstm
   :language: fcstm
   :caption: region_plain.fcstm

.. code-block:: console

   $ mkdir declared undeclared empty_list null_value
   $ echo 'name: {{ model.root_state.name }}' > declared/names.txt.j2
   $ cp declared/names.txt.j2 undeclared/
   $ cp declared/names.txt.j2 empty_list/
   $ cp declared/names.txt.j2 null_value/
   $ echo 'features: [region]' > declared/config.yaml
   $ echo '{}' > undeclared/config.yaml
   $ echo 'features: []' > empty_list/config.yaml
   $ echo 'features:' > null_value/config.yaml
   $ pyfcstm generate -i controller.fcstm -t declared -o out_declared
   $ cat out_declared/names.txt
   name: Controller
   $ pyfcstm generate -i controller.fcstm -t undeclared -o out_undeclared
   generate with template directory '...undeclared' does not support region models yet. (line 12)
   The model declares 2 regions, the first is 'Controller.Running.Safety'.
   If you write this template: its config.yaml does not list `region` under `features`. ...
   If you write the model: use a template that supports regions. Built-in templates that support regions: c, c_poll, cpp, cpp_poll, python.
     pyfcstm generate -i controller.fcstm --template c -o out_undeclared
   Or take the regions out of the model.
   $ echo $?
   1
   $ test -e out_undeclared || echo "nothing was written"
   nothing was written
   $ pyfcstm generate -i controller.fcstm -t empty_list -o out_empty_list
   generate with template directory '...empty_list' does not support region models yet. (line 12)
   ...
   $ echo $?
   1
   $ pyfcstm generate -i controller.fcstm -t null_value -o out_null_value
   generate with template directory '...null_value' does not support region models yet. (line 12)
   ...
   $ echo $?
   1
   $ pyfcstm generate -i region_plain.fcstm -t undeclared -o out_plain
   $ cat out_plain/names.txt
   name: Plain

What the records establish:

* a template that lists ``region`` renders the region model (exit status 0 and a file in the output directory);
* a template without the key, with ``features: []`` or with ``features:`` is refused for the region model: exit status 1, no output directory, and the message names the template directory;
* the same template without declaration still renders a model without regions;
* the refusal does not tell you the template is broken, it tells you that the template author has not declared region support. Select a built-in template, or declare ``region`` after the template renders regions.

The records do not show what happens with ``--clear``. The refusal comes before
the output directory is touched, so an existing directory is not cleared either.
A built-in template is never refused for regions; the refusal text for a built-in
name exists in ``pyfcstm/entry/generate.py`` but cannot be reached with the five
current templates.

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

Legal and illegal examples
--------------------------

These examples are intentionally small. They show the shape accepted or rejected
by the renderer; they are not complete production templates.

.. list-table:: Top-level examples
   :header-rows: 1

   * - Case
     - YAML
     - Result
   * - Empty config.
     - ``{}``
     - Legal. The renderer uses built-in defaults and no extra styles or helpers.
   * - Expression style.
     - ``expr_styles: {py_expr: {base_lang: python}}``
     - Legal. ``py_expr`` delegates to the Python expression renderer.
   * - Statement style.
     - ``stmt_styles: {py_stmt: {base_lang: python, assign: "{{ target }} = {{ expr }}"}}``
     - Legal. The override affects assignment rendering for that style.
   * - Unknown key.
     - ``helpers: {}``
     - Invalid. Move values under ``globals``, ``filters`` or ``tests``.
   * - Wrong root.
     - ``[expr_styles]``
     - Invalid. The root must be a mapping.
   * - Invalid ignores.
     - ``ignores: '*.tmp'``
     - Invalid. ``ignores`` must be a list of strings.

.. list-table:: Style examples
   :header-rows: 1

   * - Case
     - YAML
     - Result
   * - Canonical expression style.
     - ``expr_styles: {c_expr: {base_lang: c}}``
     - Legal. ``c_expr`` can be used with ``expr_render``.
   * - Alias expression style.
     - ``expr_styles: {node_expr: {base_lang: nodejs}}``
     - Legal. The alias resolves to ``js``.
   * - Statement style with expression language.
     - ``stmt_styles: {c_runtime: {base_lang: c, expr_lang: c_scope_expr}}``
     - Legal when ``c_scope_expr`` is also defined as an expression style.
   * - Style is scalar.
     - ``expr_styles: {bad: c}``
     - Invalid. Each style entry must be a mapping.
   * - Missing base.
     - ``stmt_styles: {bad: {assign: "{{ target }} = {{ expr }};"}}``
     - Invalid. ``base_lang`` is required.
   * - Unknown base.
     - ``expr_styles: {bad: {base_lang: ruby}}``
     - Invalid unless the renderer later adds a ``ruby`` base.

Object-loading examples
-----------------------

.. list-table:: Object-loading examples
   :header-rows: 1

   * - Form
     - YAML
     - Notes
   * - Import a helper.
     - ``filters: {snake: {type: import, from: mypkg.naming.snake}}``
     - The imported object is registered as a filter.
   * - Store a value.
     - ``globals: {project: {type: value, value: demo}}``
     - The literal value is available as ``project``.
   * - Template callable with params.
     - ``globals: {banner: {type: template, params: [name], template: "{{ name }}"}}``
     - Positional arguments bind to ``params`` and merge with keyword arguments.
   * - Template callable without params.
     - ``globals: {banner: {type: template, template: "demo"}}``
     - The callable renders the configured template without positional binding.
   * - Import target failure.
     - ``filters: {missing: {type: import, from: no.such.object}}``
     - Invalid at environment setup time; fix the Python import path.
   * - Unknown type.
     - ``globals: {x: {type: mystery, value: 1}}``
     - The remaining mapping is returned; do not use this as a public template pattern.
   * - Missing type.
     - ``globals: {x: {value: 1}}``
     - The mapping is returned as-is; use ``type: value`` when a literal value is intended.

Statement helper examples
-------------------------

.. list-table:: Statement helper calls
   :header-rows: 1

   * - Call
     - Use
     - Boundary
   * - ``{{ stmt | stmt_render(style='python') }}``
     - Render one executable statement node in Python syntax.
     - Requires a statement node, not arbitrary text.
   * - ``{{ action.operations | stmts_render(style='c_runtime') }}``
     - Render a sequence of operation nodes for a target runtime style.
     - Persistent variable and temporary-variable context matters.
   * - ``{{ action.operations | stmts_render(style='python', sep='\n\n') }}``
     - Render with a custom separator.
     - Separator changes text layout, not semantics.
   * - ``{{ action.operations | operation_stmts_render }}``
     - Echo DSL-like operation text for docs or comments.
     - Do not use as executable runtime source.

Validation branch quick reference
---------------------------------

.. list-table:: Invalid shapes and repairs
   :header-rows: 1

   * - Invalid shape
     - Error family
     - Repair
   * - Malformed YAML.
     - YAML parse error.
     - Fix indentation, quoting, or collection syntax before checking renderer facts.
   * - Comment-only file.
     - Legal empty config.
     - No repair needed; it behaves like ``{}``.
   * - ``expr_styles: []``.
     - Section type error.
     - Use a mapping from style name to style mapping.
   * - ``tests: []``.
     - Section type error.
     - Use a mapping from test name to object-loading item.
   * - ``ignores: [1]``.
     - Ignore item type error.
     - Quote each pattern as a string.
   * - ``type: template`` without ``template``.
     - Object-loading validation.
     - Add the Jinja template string.
   * - ``type: import`` without ``from``.
     - Object-loading validation.
     - Add the import path to the Python object.
   * - ``type: value`` without ``value``.
     - Object-loading validation.
     - Add the literal value or remove the object if it is unused.

Destructive output examples
---------------------------

``ignores`` and ``.git`` protection apply to scanning the template input. They
do not protect the output directory. These examples are command-facing facts:

* rendering with ``--clear`` into ``/tmp/generated`` is appropriate when that
  directory is disposable;
* rendering with ``--clear`` into a project source directory can delete files in
  that directory before generation;
* static template files keep their original bytes, while rendered files are
  written as UTF-8 text with LF newlines;
* a symlink already inside the output directory is unlinked during clear, not
  followed as a directory tree;
* the defensive ``clear-other-warning`` path exists for uncommon file types and
  should not be presented as the primary cleanup behavior.

Review checklist
----------------

A template-config reference update is incomplete unless it answers these review
questions:

* did every top-level key keep a marker and visible row;
* did every new validation branch get one legal repair and one invalid YAML
  shape;
* did English and Chinese pages cover the same canonical style names, aliases,
  statement fields, object-loading forms, helpers, and file behaviors;
* did the prose distinguish runtime statement rendering from DSL echo rendering;
* did the ``features`` row list its members, default, and validation errors in both languages;
* did any destructive output behavior mention ``--clear`` and the fact that
  input-side ``.git`` ignores do not protect output directories.
