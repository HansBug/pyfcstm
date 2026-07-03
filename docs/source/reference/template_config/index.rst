.. _sec-reference-template-config:

Template configuration reference
================================

This page is the lookup table for template ``config.yaml`` files. It records
what the renderer reads, what each section means, and which value shapes are
accepted. Use it when maintaining a template directory. For a guided task flow,
see :doc:`../../how_to/templates/index`; for renderer design rationale, see
:doc:`../../explanations/template_rendering/index`.

File contract
-------------

A template directory may contain ``config.yaml``. The renderer treats an empty
file as an empty mapping, and it creates a ``default`` expression style when no
``expr_styles.default`` entry is supplied. Unknown top-level keys fail fast.

Allowed top-level keys are:

.. list-table:: ``config.yaml`` top-level keys
   :header-rows: 1

   * - Key
     - Type
     - Purpose
   * - ``expr_styles``
     - mapping
     - Registers expression rendering styles used by ``expr_render``.
   * - ``stmt_styles``
     - mapping
     - Registers operation statement rendering styles used by ``stmt_render``
       and ``stmts_render``.
   * - ``globals``
     - mapping
     - Adds Jinja2 globals through ``pyfcstm.render.func.process_item_to_object``.
   * - ``filters``
     - mapping
     - Adds Jinja2 filters through the same object-loading mechanism.
   * - ``tests``
     - mapping
     - Adds Jinja2 tests through the same object-loading mechanism.
   * - ``ignores``
     - list of strings
     - Git-style ignore patterns for files that should not be rendered or
       copied from the template directory.

Expression styles
-----------------

Each entry under ``expr_styles`` is a mapping. It must contain ``base_lang`` and
may contain template overrides for the selected language style.

.. code-block:: yaml

    expr_styles:
      python:
        base_lang: python
      c:
        base_lang: c

Use styles from templates as filters:

.. code-block:: jinja

    {{ transition.guard | expr_render(style='python') }}
    {{ operation.value | expr_render(style='c') }}

Known expression style families include ``dsl``, ``c``, ``cpp``, ``python``,
``java``, ``js``, ``ts``, ``rust``, and ``go``. A style name in ``config.yaml``
can be template-specific, but its ``base_lang`` must normalize to one of the
registered renderer styles.

Statement styles
----------------

``stmt_styles`` follows the same pattern but targets operation statements.
Static-language templates may also supply options such as temporary-variable
rendering and type aliases.

.. code-block:: yaml

    stmt_styles:
      python:
        base_lang: python
      c:
        base_lang: c
        temp_type_aliases:
          int: int32_t
          float: double

Use the statement filters for executable operation blocks:

.. code-block:: jinja

    {{ action.operations | stmts_render(style='python') }}
    {{ operation | stmt_render(style='c') }}

Do not use ``operation_stmt_render`` or ``operation_stmts_render`` for generated
runtime code. Those helpers render DSL echo text for documentation or debugging.

Object-loading sections
-----------------------

``globals``, ``filters``, and ``tests`` use the same object loading convention.
They are useful for renderer-oriented helpers, naming helpers, or small
language-specific formatting utilities that belong to the template.

Keep target-runtime semantics in generated code or template macros. Avoid using
renderer globals as a hidden runtime.

Ignore patterns
---------------

``ignores`` uses gitignore-style patterns through ``pathspec``. The renderer
always ignores ``.git``. Add source-only notes, fixtures, or authoring helpers
when they should not be copied into generated output.

.. code-block:: yaml

    ignores:
      - README.template-notes.md
      - testdata/
      - '*.draft'

Minimal config
--------------

A minimal custom template can start with an empty mapping and one Jinja2 file:

.. code-block:: yaml

    {}

Then add styles only when the template needs target-language rendering beyond
DSL echo text.

Validation checklist
--------------------

* Keep the root value a mapping.
* Use only the allowed top-level keys.
* Give every custom style a ``base_lang``.
* Keep reusable target-language source snippets in templates or macros, not in
  Python renderer globals unless the helper is truly renderer-oriented.
* Pair config changes with a small render test or a generated artifact check.
