Template System Tutorial
========================

This tutorial is about the template system itself. The goal is not only to use
an existing built-in template, but to understand how pyfcstm turns a state
machine model into generated files so you can design, test, and maintain your
own templates.

Understand The Template System
------------------------------

What The Template System Does
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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
^^^^^^^^^^^^^^^^^^^^^^^^^^

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

Build The Template Foundation
-----------------------------

Jinja2 Essentials For Template Authors
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

pyfcstm uses Jinja2 as the template language. You do not need advanced Jinja2
metaprogramming to be productive, but you should be comfortable with:

- variable output
- ``if`` / ``elif`` / ``else``
- ``for`` loops
- ``macro``
- filters
- globals
- tests

If you want the official Jinja learning path rather than only the minimal
examples in this tutorial, continue with:

- `Jinja Template Designer Documentation <https://jinja.palletsprojects.com/en/stable/templates/>`_
- `Jinja API Documentation <https://jinja.palletsprojects.com/en/stable/api/>`_

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

Beyond that minimum, template authors usually need a few more Jinja features in
real template work:

- comments: ``{# ... #}``
- template reuse: ``{% import ... %}``, ``{% from ... import ... %}``
- whitespace control: ``{%-`` and ``-%}``
- filter chains: ``{{ value | filter_a | filter_b }}``
- tests such as ``{% if value is defined %}``

Those features show up constantly in templates. For example:

.. code-block:: jinja

   {# avoid an extra trailing blank line #}
   {% for state in model.walk_states() -%}
   - {{ state.path | join('.') }}
   {% endfor %}

   {% if state.doc is defined %}
   # {{ state.doc }}
   {% endif %}

   {% from 'macros.j2' import render_state_block %}
   {{ render_state_block(model.root_state) }}

Two practical rules are worth calling out:

1. Keep reusable naming and formatting logic in helpers instead of copying the
   same Jinja expression across many files.
2. Use macros for repeated template structure, and use ``config.yaml`` helpers
   for repeated naming and renderer-facing logic.

The Role Of ``config.yaml``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

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

Use The Rendering Interfaces
----------------------------

Understanding ``expr_render``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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

Parameter overview:

.. list-table::
   :header-rows: 1

   * - Field
     - Required
     - Meaning
     - Typical values
   * - ``node``
     - Yes
     - The single expression node to render
     - ``transition.guard.to_ast_node()``, ``some_expr``, ``1``, ``True``
   * - ``style``
     - No
     - Which expression style to use
     - ``python``, ``c``, ``default``, or a custom style from ``config.yaml``

The default behavior of ``style`` matters:

- on a top-level call, omitting ``style=...`` uses ``default``
- inside recursive expression rendering, omitting ``style=...`` inherits the
  current style

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

How ``expr_render`` Resolves Template Keys
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is the part template authors usually need spelled out. When you override
``expr_styles`` in ``config.yaml``, you are not replacing "a whole language".
You are overriding template entries for specific expression-node shapes.

The matching rule is:

1. try the most specific key first
2. if it does not exist, fall back to the generic key for that node family
3. if that still does not exist, fall back to ``default``

The key patterns that matter most are:

.. list-table::
   :header-rows: 1

   * - Key form
     - Matches
     - Example
     - Typical use
   * - ``Float``
     - float literals
     - ``3.14``
     - change float formatting
   * - ``Integer``
     - decimal integer literals
     - ``42``
     - change integer formatting
   * - ``Boolean``
     - boolean literals
     - target-language ``true`` / ``false`` spellings
     - map boolean literals
   * - ``Constant``
     - DSL constant nodes
     - ``pi``, ``e``, ``tau``
     - map constants to ``Math.PI``, ``math.Pi``, and so on
   * - ``HexInt``
     - hexadecimal integers
     - ``0xFF``
     - preserve hex output
   * - ``Paren``
     - parenthesized expressions
     - ``(a + b)``
     - control parenthesis preservation
   * - ``Name``
     - variable names
     - ``counter``
     - scope remapping such as ``scope['counter']``
   * - ``UFunc``
     - any unary function call
     - ``sin(x)``
     - define generic function-call rendering
   * - ``UFunc(sin)``
     - one specific unary function
     - ``sin(x)``
     - special-case one function
   * - ``UnaryOp``
     - any unary operator
     - ``-x``
     - define generic unary rendering
   * - ``UnaryOp(!)``
     - one specific unary operator
     - ``!flag``
     - map ``!`` to ``not``, for example
   * - ``BinaryOp``
     - any binary operator
     - ``a + b``
     - define generic binary rendering
   * - ``BinaryOp(**)``
     - one specific binary operator
     - ``a ** b``
     - map exponentiation to ``pow(...)``
   * - ``ConditionalOp``
     - ternary conditional expressions
     - ``cond ? a : b``
     - map to the target-language ternary form
   * - ``default``
     - final fallback
     - when no more specific key exists
     - last-resort rendering

The important precedence points are:

- ``UFunc(sin)`` wins over ``UFunc``
- ``UnaryOp(!)`` wins over ``UnaryOp``
- ``BinaryOp(**)`` wins over ``BinaryOp``
- node families such as ``Name``, ``Float``, and ``Integer`` match directly by
  their node type name

That is why a Python-style override such as:

.. code-block:: yaml

   expr_styles:
     default:
       base_lang: python
       UnaryOp(!): 'not {{ node.expr | expr_render }}'
       BinaryOp(&&): '{{ node.expr1 | expr_render }} and {{ node.expr2 | expr_render }}'
       BinaryOp(||): '{{ node.expr1 | expr_render }} or {{ node.expr2 | expr_render }}'

does not replace the whole Python expression system. It only says:

- override ``!``
- override ``&&``
- override ``||``
- keep using the inherited Python templates for everything else

That is the core advantage of the style system: most template authors should
override a few keys, not copy an entire expression-style dictionary.

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

How To Override Those Keys
~~~~~~~~~~~~~~~~~~~~~~~~~~

The most common override cases are these.

1. Override only name mapping:

.. code-block:: yaml

   expr_styles:
     default:
       base_lang: python
       Name: "scope[{{ node.name | tojson }}]"

Effect:

- ``counter + 1`` becomes ``scope["counter"] + 1``
- everything else still uses the inherited Python style

2. Override only one operator:

.. code-block:: yaml

   expr_styles:
     default:
       base_lang: c
       BinaryOp(**): 'pow({{ node.expr1 | expr_render }}, {{ node.expr2 | expr_render }})'

Effect:

- ``a ** b`` becomes ``pow(a, b)``
- all other binary operators keep the inherited C behavior

3. Override only one function:

.. code-block:: yaml

   expr_styles:
     default:
       base_lang: python
       UFunc(sin): 'fast_sin({{ node.expr | expr_render }})'

Effect:

- ``sin(x)`` becomes ``fast_sin(x)``
- ``cos(x)``, ``sqrt(x)``, and the rest still use the inherited Python style

The anti-pattern to avoid is:

- copying ``Float`` / ``Integer`` / ``BinaryOp`` / ``UFunc`` just to change one
  ``Name``
- repeating dozens of unrelated keys to customize one operator
- pushing expression strategy into ad hoc Jinja snippets instead of keeping it
  in styles

A practical refactor looks like this.

Before:

.. code-block:: jinja

   if {{ transition.guard.to_ast_node() | expr_render(style='python') }}:
       ...

   value = {{ some_expr | expr_render(style='python') }}

After:

.. code-block:: yaml

   expr_styles:
     default:
       base_lang: python
     python_scope_expr:
       base_lang: python
       Name: "scope[{{ node.name | tojson }}]"

.. code-block:: jinja

   if {{ transition.guard.to_ast_node() | expr_render }}:
       ...

   value = {{ some_expr | expr_render }}

Effect:

- shorter template bodies
- more centralized target-language decisions
- fewer chances to forget or mismatch the intended style

Understanding ``stmt_render`` And ``stmts_render``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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

Parameter overview for ``stmt_render``:

.. list-table::
   :header-rows: 1

   * - Field
     - Required
     - Meaning
     - Typical values
   * - ``node``
     - Yes
     - One operation statement
     - ``action.operations[0]``
   * - ``style``
     - No
     - Which statement style to use
     - ``python``, ``c``, ``default``
   * - ``state_vars``
     - No
     - Names that should be treated as persistent state variables
     - ``('counter', 'flag')``
   * - ``var_types``
     - No
     - Variable type mapping, mainly for static-language styles
     - ``{'counter': 'int', 'ratio': 'float'}``
   * - ``visible_names``
     - No
     - Temporary names already visible before this statement
     - ``('tmp', 'error')``
   * - ``visible_var_types``
     - No
     - Type mapping for already-visible temporary names
     - ``{'tmp': 'int'}``
   * - ``indent``
     - No
     - One indentation unit
     - ``'    '``, ``'  '``
   * - ``level``
     - No
     - Initial indentation depth
     - ``0``, ``1``, ``2``

Parameter overview for ``stmts_render``:

.. list-table::
   :header-rows: 1

   * - Field
     - Required
     - Meaning
     - Typical values
   * - ``nodes``
     - Yes
     - A sequence of operation statements
     - ``action.operations``
   * - ``style``
     - No
     - Which statement style to use
     - ``python``, ``c``, ``default``
   * - ``state_vars``
     - No
     - Names that should be treated as persistent state variables
     - ``('counter', 'flag')``
   * - ``var_types``
     - No
     - Variable type mapping, mainly for static-language styles
     - ``{'counter': 'int', 'ratio': 'float'}``
   * - ``visible_names``
     - No
     - Temporary names already visible before this block
     - ``('tmp', 'error')``
   * - ``visible_var_types``
     - No
     - Type mapping for already-visible temporary names
     - ``{'tmp': 'int'}``
   * - ``indent``
     - No
     - One indentation unit
     - ``'    '``, ``'  '``
   * - ``level``
     - No
     - Initial indentation depth
     - ``0``, ``1``, ``2``
   * - ``sep``
     - No
     - Separator between top-level rendered statements
     - ``'\\n'``

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

A common refactor is to stop hand-writing statement expansion.

Before:

.. code-block:: jinja

   {% for op in action.operations %}
   {{ op.target.name }} = {{ op.expr.to_ast_node() | expr_render(style='python') }}
   {% endfor %}

Problems with that approach:

- it only covers the simplest assignment shape
- temporary-variable semantics are easy to get wrong
- ``if / else if / else`` quickly forces you to reimplement a statement renderer

After:

.. code-block:: jinja

   {{ action.operations | stmts_render(style='python') }}

Effect:

- assignments, temporaries, and branches all go through one renderer
- the template gets shorter and less error-prone
- scope or typing changes become style changes rather than template rewrites

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
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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

When you want the full model surface, continue with :doc:`../../api_doc/model/index`.

That API documentation is the right place to inspect:

- what :class:`pyfcstm.model.StateMachine` exposes
- what is available on states, transitions, events, and lifecycle-action objects
- how model objects and expression nodes are organized

Design Real Templates
---------------------

Generation Scale And Template Shape
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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

To make that example more concrete, assume the input DSL is:

.. code-block:: fcstm

   def int counter = 0;

   state TrafficLight {
       [*] -> Red;

       state Red;
       state Green;
   }

Then the rendered ``out/summary.txt`` will look like:

.. code-block:: text

   Root state: TrafficLight

   Variables:
   - int counter

   States:
   - TrafficLight
   - TrafficLight.Red
   - TrafficLight.Green

That kind of concrete output check is useful because it lets you see the
generated shape immediately instead of reasoning only from template source.

Built-In Templates
------------------

The render system is general, but the repository also ships built-in templates
that serve as real reference implementations.

Current built-in templates:

- ``python``
  - status: current built-in template
  - design position: reference implementation for template-system structure and
    simulator-aligned runtime semantics
- ``c``
  - status: current built-in template
  - design position: self-contained generated C runtime with a documented
    public API and stronger focus on deployment/runtime integration
- ``c_poll``
  - status: current built-in template
  - design position: self-contained generated C runtime with hook-polled event
    acquisition, intended for scan-cycle and control-loop style integrations

For built-in templates, pyfcstm also emits generated usage guides into the
output directory. In practice, users will find ``README.md`` and
``README_zh.md`` alongside the generated artifacts, and those generated
documents are the primary place to explain target-specific usage details.

python - Reference Runtime Template For Simulator-Aligned Codegen
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``python`` template is the clearest reference implementation for how the
template system comes together end to end.

Its current design position is:

- a reference implementation for built-in template layout
- a single-file runtime template
- generated README templates for end users
- runtime behavior aligned with the simulator
- protected-hook extension points for abstract actions

If you want the most approachable reference for template structure, helper
design, generated runtime shape, and simulator-aligned behavior, start from the
``python`` template under ``templates/python/`` and the generated
``README.md`` / ``README_zh.md`` it emits.

c - Self-Contained Generated Runtime For Native Integration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``c`` template is the native-runtime-oriented built-in option. It generates
a self-contained runtime around ``machine.h`` and ``machine.c`` rather than a
single-file Python runtime, but it still follows the same template-system
model.

Its current design position is:

- a generated C runtime intended for direct embedding and integration
- explicit public header/runtime API instead of Python import-based usage
- generated ``README.md`` / ``README_zh.md`` as the primary user-facing
  integration guide
- runtime tests and alignment tests that validate generated behavior against
  the simulator where applicable

If you want the native-runtime example, go to ``templates/c/`` and treat the
generated ``README.md`` / ``README_zh.md`` in output directories as the
authoritative integration guide for end users.

c_poll - Hook-Polled Runtime For Scan-Cycle Control Integration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``c_poll`` template is closely related to ``c`` and reuses the same broad
runtime direction: generated ``machine.h`` and ``machine.c``, a documented
public API, and generated user-facing ``README.md`` / ``README_zh.md`` files.

The key design difference is the event-input model:

- ``c`` expects the integration layer to collect events first and then submit a
  per-cycle event-id set into ``cycle(...)``
- ``c_poll`` expects the integration layer to install generated
  ``check_xxx`` hooks once, and the runtime then queries those hooks lazily
  while deciding transitions inside ``cycle()``

That difference matters because it changes who owns event observation:

- in ``c``, the application owns event collection and passes a normalized event
  set into the runtime
- in ``c_poll``, the runtime owns event observation timing and asks
  "is this event active right now?" through the installed event-check table

This makes ``c_poll`` a better fit for many real control-system and embedded
integration patterns, for example:

- cyclic scan loops that read current inputs every control tick
- PLC-like logic where transition conditions are evaluated against the current
  sampled world state
- embedded control systems where "event active this cycle" is derived from
  input pins, sensors, fieldbus snapshots, or shared process images
- integrations that do not already have a clean external event-dispatch layer

In practical terms, choose ``c`` when your surrounding system already has a
clear event aggregation or dispatch step and you want to feed explicit event
sets into the runtime. Choose ``c_poll`` when your system is naturally
cycle-driven and event truth is better expressed as polled checks over the
current input snapshot.

Test And Consolidate
--------------------

Testing Templates
^^^^^^^^^^^^^^^^^

Template work should be tested at multiple levels.

Start with a template-author workflow, not with a giant machine:

1. prepare one tiny DSL sample for the exact behavior you are implementing
2. render into a temporary output directory
3. inspect the generated file names, structure, indentation, and variable mapping
4. if this is a runtime template, actually import and execute the generated code
5. turn that sample into a regression test before expanding the template further

Do not debug a new template against a large state machine first. Template bugs
and model complexity compound very quickly.

Renderer-Level Tests
~~~~~~~~~~~~~~~~~~~~

Use :class:`pyfcstm.render.StateMachineCodeRenderer` directly when you want to
check file output for a controlled model.

Typical checks:

- expected files exist
- copied static files stay unchanged
- rendered files contain the expected text
- custom ``expr_styles`` and ``stmt_styles`` behave correctly

Generated-Artifact Tests
~~~~~~~~~~~~~~~~~~~~~~~~

For runtime templates, do not stop at string comparison. Import the generated
artifact and execute it.

Typical checks:

- generated Python files import successfully
- generated public API matches the template contract
- generated code behaves correctly on simple state-machine scenarios

Behavior-Alignment Tests
~~~~~~~~~~~~~~~~~~~~~~~~

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
~~~~~~~~~~~~~~~~~~~~

Add CLI tests when your template is intended to be used through the command line:

- generate with ``pyfcstm generate -t ./your_template``
- verify output files exist
- import or run the generated artifact
- check one minimal behavior path

When template debugging gets stuck, a good triage order is:

1. check whether the helper or style in ``config.yaml`` already does what you think it does
2. check whether the object you pass into ``expr_render`` / ``stmt_render`` / ``stmts_render`` is the right one
3. if you suspect the DSL block shape rather than the target-language rendering, echo it first with ``operation_stmt_render`` or ``operation_stmts_render``
4. if the generated file text looks correct but behavior is wrong, move to generated-artifact tests

When To Put Logic Where
^^^^^^^^^^^^^^^^^^^^^^^

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

Summary
^^^^^^^

The key ideas for template authors are:

- think in terms of ``StateMachine`` model in, file tree out
- keep renderer-facing logic in ``config.yaml``
- keep repeated structure in macros
- learn the official Jinja material for syntax depth, then apply pyfcstm-specific rules here
- test templates at renderer, generated-artifact, and CLI levels when needed

Once these pieces are clear, writing a new template becomes a disciplined
engineering task rather than trial-and-error Jinja editing.
