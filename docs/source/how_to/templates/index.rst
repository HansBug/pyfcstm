.. _sec-how-to-templates:

Template author tasks
=====================

This guide shows how to create and maintain a custom template directory. It is
for template authors, not for users who only want a built-in target. If you only
want generated code, start with :doc:`../generation/index` and
:doc:`../../reference/builtin_templates/index`.

Create a minimal template
-------------------------

A template directory needs a ``config.yaml`` file and one or more output files.
Files ending in ``.j2`` are rendered; other files are copied as static assets.

.. code-block:: text

    my_template/
    ├── config.yaml
    ├── machine.py.j2
    └── README.md

A tiny ``config.yaml`` can be an empty mapping:

.. code-block:: yaml

    {}

A minimal rendered file can start by inspecting the model:

.. code-block:: jinja

    # Generated from {{ model.name }}
    STATES = [
    {%- for state in model.walk_states() %}
        "{{ state.name }}",
    {%- endfor %}
    ]

Render it with a temporary output directory:

.. code-block:: bash

    pyfcstm generate \
        -i docs/source/tutorials/cli/simple_machine.fcstm \
        -t my_template \
        -o /tmp/pyfcstm-template-check \
        --clear

Use built-in templates through ``--template`` instead of pointing users at the
repository ``templates/`` source tree. Custom template development is the reason
to use ``-t`` / ``--template-dir``.

Render expressions and statements
---------------------------------

Add expression and statement styles in ``config.yaml`` when templates need
language-specific syntax:

.. code-block:: yaml

    expr_styles:
      python:
        base_lang: python
    stmt_styles:
      python:
        base_lang: python

Then use renderer filters in ``.j2`` files:

.. code-block:: jinja

    {{ transition.guard | expr_render(style='python') }}
    {{ action.operations | stmts_render(style='python') }}

Use ``operation_stmt_render`` only when you deliberately want DSL-like echo
text. Runtime templates should use ``stmt_render`` and ``stmts_render``.

Organize helper logic
---------------------

Prefer this order when deciding where helper logic belongs:

1. Put repeated file structure in Jinja2 macros.
2. Put target-language runtime behavior in generated code.
3. Put naming or renderer-oriented helpers in ``config.yaml`` globals, filters,
   or tests.
4. Avoid adding Python package code for one template unless the helper is shared
   production behavior.

For the exact ``config.yaml`` shape, see
:doc:`../../reference/template_config/index`.

Validate a custom template
--------------------------

For each representative DSL fixture:

1. Run ``pyfcstm generate`` into a clean temporary directory.
2. Inspect the generated file tree.
3. Run the target-language formatter or compiler when applicable.
4. Execute a small generated-runtime smoke test when the template emits runtime
   code.
5. If the template is intended to match simulator semantics, compare its trace
   with ``pyfcstm simulate`` or an existing alignment fixture.

Keep validation proportional to the target. A documentation-only template might
need only render and formatting checks; a runtime template needs generated code
execution.

Keep generated artifacts professional
-------------------------------------

Generated files should be readable and formatter-friendly. For the repository's
formatter expectations, follow the template formatter guidance in ``CLAUDE.md``:
``ruff`` for Python, ``clang-format`` for C/C++/Java, ``dprint`` for JavaScript
and TypeScript, ``rustfmt`` for Rust, and ``gofmt`` for Go.

Do not add complex template machinery solely to satisfy a weak formatter-only
rewrite when semantics or maintainability would suffer.
