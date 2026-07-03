.. _sec-how-to-templates-zh:

模板作者任务指南
================

本指南面向自定义模板作者，说明如何创建和维护模板目录。只想使用内置模板生成代码的用户，应从 :doc:`../generation/index_zh` 和 :doc:`../../reference/builtin_templates/index_zh` 开始。

创建最小模板
------------

模板目录需要 ``config.yaml`` 和一个或多个输出文件。以 ``.j2`` 结尾的文件会被渲染；其他文件会作为静态资源复制。

.. code-block:: text

    my_template/
    ├── config.yaml
    ├── machine.py.j2
    └── README.md

最小 ``config.yaml`` 可以是空 mapping：

.. code-block:: yaml

    {}

最小模板文件可以先检查 model：

.. code-block:: jinja

    # Generated from {{ model.name }}
    STATES = [
    {%- for state in model.walk_states() %}
        "{{ state.name }}",
    {%- endfor %}
    ]

用临时输出目录验证：

.. code-block:: bash

    pyfcstm generate \
        -i docs/source/tutorials/cli/simple_machine.fcstm \
        -t my_template \
        -o /tmp/pyfcstm-template-check \
        --clear

内置模板的用户主路径是 ``--template``，不要把仓库源码 ``templates/`` 路径写成普通用户主路径。只有开发自定义模板时才使用 ``-t`` / ``--template-dir``。

渲染表达式和语句
----------------

如果模板需要目标语言语法，在 ``config.yaml`` 中添加表达式和语句样式：

.. code-block:: yaml

    expr_styles:
      python:
        base_lang: python
    stmt_styles:
      python:
        base_lang: python

然后在 ``.j2`` 文件中使用 renderer filters：

.. code-block:: jinja

    {{ transition.guard | expr_render(style='python') }}
    {{ action.operations | stmts_render(style='python') }}

``operation_stmt_render`` 只适合有意输出 DSL-like 文本的场景。runtime 模板应使用 ``stmt_render`` 和 ``stmts_render``。

组织辅助逻辑
------------

决定辅助逻辑放在哪里时，优先顺序如下：

1. 重复文件结构放入 Jinja2 macros。
2. 目标 runtime 行为放入生成代码。
3. 命名或 renderer 侧辅助逻辑放入 ``config.yaml`` globals、filters 或 tests。
4. 只有跨模板共享的生产行为才应进入 Python 包代码。

``config.yaml`` 的准确字段形状见 :doc:`../../reference/template_config/index_zh`。

验证自定义模板
--------------

对每个代表性 DSL fixture：

1. 运行 ``pyfcstm generate`` 到干净临时目录。
2. 检查生成文件树。
3. 按目标语言运行 formatter 或 compiler。
4. 如果模板生成 runtime 代码，执行一个小型 smoke test。
5. 如果模板声称与 simulator 对齐，将 trace 与 ``pyfcstm simulate`` 或已有 alignment fixture 对比。

生成产物质量
------------

生成文件应该可读、可格式化。模板工作遵循 ``CLAUDE.md`` 中的 formatter 约定：Python 用 ``ruff``，C/C++/Java 用 ``clang-format``，JavaScript/TypeScript 用 ``dprint``，Rust 用 ``rustfmt``，Go 用 ``gofmt``。

不要为了弱 formatter-only rewrite 而引入损害语义或可维护性的复杂模板机制。
