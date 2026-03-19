Template System Tutorial
========================

This tutorial is about the template system itself. The goal is not only to use
an existing built-in template, but to understand how pyfcstm turns a state
machine model into generated files so you can design, test, and maintain your
own templates.

What The Template System Does
-----------------------------

pyfcstm follows a clear separation of responsibilities:

- The DSL parser reads ``.fcstm`` text and builds an AST.
- The model layer converts the AST into a :class:`pyfcstm.model.StateMachine`.
- The renderer loads a template directory and renders files from that model.
- The template decides what output files look like.

The renderer is not a compiler backend by itself. It does not know what your
target project structure should be, what naming conventions you want, or how
large the generated runtime should be. Those decisions belong to the template.

The simplest mental model is:

.. code-block:: text

   DSL text
     -> StateMachine model
     -> StateMachineCodeRenderer(template_dir)
     -> rendered files in output_dir

Template authors should think in terms of "model in, file tree out".

Current Rendering Boundaries
----------------------------

The current renderer has a few important boundaries that shape template design:

- Files ending in ``.j2`` are rendered through Jinja2.
- Non-``.j2`` files are copied as-is.
- Directory structure is preserved.
- Output file names are fixed by template file names.
  ``machine.py.j2`` becomes ``machine.py``.
- Ignore patterns come from ``config.yaml`` and use gitignore-style matching.

This means a template controls file contents very well, but does not currently
control output file names dynamically. If you need a file called
``TrafficLightMachine.py``, that is not a template-only change today. You would
need renderer support for templated output paths.

Template Directory Anatomy
--------------------------

A template directory is usually small and explicit:

.. code-block:: text

   my_template/
   ├── config.yaml
   ├── machine.py.j2
   ├── README.md
   ├── README.md.j2
   └── static/
       └── helper.txt

Typical file roles:

- ``config.yaml``: renderer configuration, helper definitions, style overrides,
  and ignore rules.
- ``*.j2``: rendered files.
- static files: copied to the output directory unchanged.
- template ``README`` files: documentation for template maintainers.
- generated ``README`` templates such as ``README.md.j2``: documentation for
  users of the generated output.

This distinction matters. Template-maintainer docs explain how the template is
organized. Generated docs explain how to use the generated artifact.

Jinja2 Essentials For Template Authors
--------------------------------------

pyfcstm uses Jinja2 as the template language. You do not need advanced Jinja2
metaprogramming to be productive, but you should be comfortable with:

- variable output
- ``if`` / ``elif`` / ``else``
- ``for`` loops
- ``macro``
- filters
- globals
- tests

Minimal examples:

.. code-block:: jinja

   {{ model.root_state.name }}

   {% for state in model.walk_states() %}
   - {{ state.name }}
   {% endfor %}

   {% if state.is_leaf_state %}
   leaf
   {% else %}
   composite
   {% endif %}

   {% macro state_id(state) -%}
   {{ state.path | join('_') }}
   {%- endmacro %}

Two practical rules are worth calling out:

1. Keep reusable naming and formatting logic in helpers instead of copying the
   same Jinja expression across many files.
2. Use macros for repeated template structure, and use ``config.yaml`` helpers
   for repeated naming and renderer-facing logic.

The Role Of ``config.yaml``
---------------------------

``config.yaml`` is the main integration point between the renderer and your
template. It usually contains:

- ``expr_styles``
- ``stmt_styles``
- ``globals``
- ``filters``
- ``tests``
- ``ignores``

Example:

.. code-block:: yaml

   expr_styles:
     python_scope_expr:
       base_lang: python
       Name: "scope[{{ node.name | tojson }}]"

   globals:
     state_path:
       type: template
       params: [state]
       template: "{{ state.path | join('.') }}"

   filters:
     state_path:
       type: template
       params: [state]
       template: "{{ state.path | join('.') }}"

   ignores:
     - 'README.md'

How to think about each section:

- ``expr_styles``: customize expression rendering for a target language or a
  target scope.
- ``stmt_styles``: customize operational-statement rendering, including
  temporary-variable handling for static or dynamic languages.
- ``globals``: helper functions or values available as template globals.
- ``filters``: transformation helpers used in ``{{ value | filter_name }}``.
- ``tests``: Jinja2 tests for conditions such as ``value is my_test``.
- ``ignores``: files or directories the renderer should skip.

Use ``config.yaml`` when the logic is renderer-oriented or naming-oriented.
Use a Jinja2 macro when the logic is mainly about repeated file structure.

Understanding ``expr_render``
-----------------------------

``expr_render`` is the expression-level renderer. Use it when you need one DSL
expression rendered into a target-language expression string.

Quick selection rule:

- If the input is one expression node, use ``expr_render``
- If the input is one operation statement, use ``stmt_render``
- If the input is a whole block such as ``action.operations``, use
  ``stmts_render``

Typical examples:

.. code-block:: jinja

   {{ transition.guard.to_ast_node() | expr_render(style='python') }}
   {{ some_expr | expr_render(style='c') }}

What it is for:

- guard expressions
- assigned values
- effect conditions
- custom naming or scope remapping for expression nodes

Typical input shapes:

- one ``pyfcstm.model.expr`` node
- one DSL AST expression node such as ``guard.to_ast_node()``
- a primitive literal such as ``1`` or ``True`` when you intentionally want
  it normalized through the expression renderer

What it returns:

- one target-language expression string
- not a complete statement
- usually not something with indentation or branch structure

What it is not for:

- full operation blocks
- assignment statements
- ``if / else if / else`` statement trees

If you need executable statement output, use ``stmt_render`` or
``stmts_render`` instead.

How style inheritance works:

- each custom style starts from ``base_lang``
- you only override the node mappings you actually need
- recursive rendering inside that style inherits the current style unless you
  explicitly pass another one

That last point matters. If you define:

.. code-block:: yaml

   expr_styles:
     python_scope_expr:
       base_lang: python
       Name: "scope[{{ node.name | tojson }}]"

then a nested expression such as ``counter + 1`` will continue using
``python_scope_expr`` for the inner ``Name`` node. You do not need to re-copy
every built-in operator template just to keep recursion aligned.

One more practical detail matters in real templates:

- when a template is rendered by :class:`pyfcstm.render.StateMachineCodeRenderer`,
  calling ``expr_render`` without ``style=...`` uses the ``default`` expression
  style from ``config.yaml``
- if you define ``default`` as a thin wrapper over ``python``, most template
  sites no longer need to spell out ``style='python'`` repeatedly

Understanding ``stmt_render`` And ``stmts_render``
--------------------------------------------------

``stmt_render`` and ``stmts_render`` are the statement-level counterparts to
``expr_render``.

Use:

- ``stmt_render`` for one operation statement
- ``stmts_render`` for a sequence of statements, usually a full action block

Typical input shapes:

- ``stmt_render`` takes one ``OperationStatement`` or one DSL operational AST
  statement
- ``stmts_render`` takes an iterable of those statements, for example
  ``action.operations``

Examples:

.. code-block:: jinja

   {{ one_statement | stmt_render(style='python') }}

   {{ action.operations | stmts_render(style='python') }}

They are the correct entry points when the DSL block may contain:

- assignments
- temporary variables
- ``if / else if / else``
- nested branches

What they return:

- executable target-language statement text
- indentation-aware multi-line output
- branch structure that still matches DSL block semantics

For template authors, the most important semantic detail is that statement
rendering distinguishes persistent state variables from block-local temporary
variables.

In renderer-driven template rendering, if you do not explicitly pass
``state_vars`` or ``var_types``, :class:`pyfcstm.render.StateMachineCodeRenderer`
automatically injects defaults from ``model.defines``. That means most
templates can simply write:

.. code-block:: jinja

   {{ action.operations | stmts_render(style='python') }}

instead of repeatedly spelling out the full state-variable set.

Why this matters:

- persistent variables should render to the target state container such as
  ``scope['counter']`` or ``scope->counter``
- temporary variables should stay local to the block
- branch-local temporaries should follow the same visibility rules as the
  runtime semantics

Built-in statement styles already encode these target-language conventions for
``dsl``, ``c``, ``cpp``, ``python``, ``java``, ``js``, ``ts``, ``rust``, and
``go``.

One more distinction is important:

- ``operation_stmt_render`` and ``operation_stmts_render`` are useful when you
  want DSL-text display
- ``stmt_render`` and ``stmts_render`` are the correct tools for target-language
  code generation

If you are generating executable code, prefer ``stmt_render`` /
``stmts_render``.

The fastest way to avoid misuse is to think in examples:

.. list-table::
   :header-rows: 1

   * - Goal
     - Input
     - Correct filter
     - Typical output shape
   * - Render one guard expression
     - ``transition.guard.to_ast_node()``
     - ``expr_render``
     - ``counter > 10``
   * - Render one assignment statement
     - one item from ``action.operations``
     - ``stmt_render``
     - ``scope['counter'] = scope['counter'] + 1``
   * - Render one whole action block
     - ``action.operations``
     - ``stmts_render``
     - multiple statements with indentation and nested ``if`` blocks

Common mistakes:

- feeding ``action.operations`` into ``expr_render`` and expecting a block
- feeding a guard expression into ``stmts_render`` and expecting it to become a
  valid ``if`` statement automatically
- using ``operation_stmts_render`` when the real goal is target-language code
  rather than DSL echo text

Template Context: What You Can Access
-------------------------------------

Rendered templates receive the state machine model as ``model``. In practice,
template authors often use:

- ``model.root_state``
- ``model.defines``
- ``model.walk_states()``
- state paths, parent/child relationships, events, actions, transitions

Example:

.. code-block:: jinja

   Root: {{ model.root_state.name }}

   Variables:
   {% for def_item in model.defines.values() %}
   - {{ def_item.type }} {{ def_item.name }}
   {% endfor %}

   States:
   {% for state in model.walk_states() %}
   - {{ state.path | join('.') }}
   {% endfor %}

When you are unsure what the model exposes, inspect existing templates and unit
tests, especially the template tests and model tests that walk real state
machines.

Generation Scale And Template Shape
-----------------------------------

Template authors need a clear idea of how output size scales:

- one template file usually produces one output file
- output size often scales with the number of states, transitions, events, and
  lifecycle actions
- nested loops and repeated inline expressions can quickly make templates hard
  to read and hard to maintain

Practical guidance:

- move repeated naming logic into helpers
- move repeated structural fragments into macros
- prefer one clear expansion pass over many nearly-identical blocks
- keep generated code readable enough that downstream users can debug it

For large generated runtimes, readability is a feature, not decoration. The
template should not rely on a formatter as a crutch for fundamentally messy
structure.

Minimal Template From Scratch
-----------------------------

The fastest way to learn the system is to write a tiny template first.

Directory:

.. code-block:: text

   demo_template/
   ├── config.yaml
   └── summary.txt.j2

``config.yaml``:

.. code-block:: yaml

   globals:
     state_path:
       type: template
       params: [state]
       template: "{{ state.path | join('.') }}"

``summary.txt.j2``:

.. code-block:: jinja

   Root state: {{ model.root_state.name }}

   Variables:
   {% for def_item in model.defines.values() %}
   - {{ def_item.type }} {{ def_item.name }}
   {% endfor %}

   States:
   {% for state in model.walk_states() %}
   - {{ state | state_path }}
   {% endfor %}

Render it with:

.. code-block:: bash

   pyfcstm generate -i ./machine.fcstm -t ./demo_template -o ./out

This is enough to verify the full renderer path before you attempt a large
runtime template.

Testing Templates
-----------------

Template work should be tested at multiple levels.

Renderer-Level Tests
^^^^^^^^^^^^^^^^^^^^

Use :class:`pyfcstm.render.StateMachineCodeRenderer` directly when you want to
check file output for a controlled model.

Typical checks:

- expected files exist
- copied static files stay unchanged
- rendered files contain the expected text
- custom ``expr_styles`` and ``stmt_styles`` behave correctly

Generated-Artifact Tests
^^^^^^^^^^^^^^^^^^^^^^^^

For runtime templates, do not stop at string comparison. Import the generated
artifact and execute it.

Typical checks:

- generated Python files import successfully
- generated public API matches the template contract
- generated code behaves correctly on simple state-machine scenarios

Behavior-Alignment Tests
^^^^^^^^^^^^^^^^^^^^^^^^

If a template is intended to match :class:`pyfcstm.simulate.SimulationRuntime`,
keep alignment tests that compare both runtimes on the same DSL samples.

This level catches semantic drift in:

- transition selection
- initial transitions
- pseudo-state handling
- aspect actions
- hot start
- temporary-variable scope

CLI End-To-End Tests
^^^^^^^^^^^^^^^^^^^^

Add CLI tests when the public user path matters, especially for built-in
templates:

- generate with ``pyfcstm generate --template ...``
- verify output files exist
- import or run the generated artifact
- check one minimal behavior path

Built-In Template Publication Chain
-----------------------------------

Built-in templates are maintained as source directories under ``templates/``,
then packaged for runtime distribution.

Current chain:

.. code-block:: text

   templates/<name>/
     -> make tpl
     -> pyfcstm/template/<name>.zip + index.json
     -> extract_template(name, output_dir)
     -> StateMachineCodeRenderer(extracted_dir)

This is important for template authors because a built-in template is not just
"a folder in the repo". It also has a packaging and extraction path that must
stay healthy.

That is why built-in template changes should usually be validated through both:

- direct source-template rendering
- packaged-template extraction and rendering

When To Put Logic Where
-----------------------

A common source of template sprawl is putting logic in the wrong place.

Use ``config.yaml`` helpers when:

- the logic is naming-related
- the same helper is reused across multiple files
- the template would otherwise duplicate long Jinja expressions

Use Jinja2 macros when:

- the logic is mostly structural
- a repeated block has many lines
- the output layout, not the helper interface, is the main concern

Inline logic in a ``.j2`` file only when:

- it is local to that file
- it is short
- extracting it would make the template harder to read

Case Study: The Built-In ``python`` Template
--------------------------------------------

The built-in ``python`` template is a good example of how the template system
comes together, but it is still just one instance.

It demonstrates:

- a single-file runtime template
- generated README templates
- helper-driven naming in ``config.yaml``
- runtime behavior aligned with the simulator
- protected-hook extension points for abstract actions

Useful files to inspect:

- ``templates/python/config.yaml``
- ``templates/python/machine.py.j2``
- ``templates/python/README.md.j2``
- ``test/template/python/test_runtime.py``
- ``test/template/python/test_runtime_alignment.py``

If you want to build your own template, study the ``python`` template as an
example of one solution, not as the definition of the entire template system.

Summary
-------

The key ideas for template authors are:

- think in terms of ``StateMachine`` model in, file tree out
- keep renderer-facing logic in ``config.yaml``
- keep repeated structure in macros
- test templates at renderer, generated-artifact, and CLI levels when needed
- remember the packaging path for built-in templates

Once these pieces are clear, writing a new template becomes a disciplined
engineering task rather than trial-and-error Jinja editing.
