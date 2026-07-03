.. _sec-reference-template-config-zh:

模板配置参考
============

本页是模板 ``config.yaml`` 的查准事实表。维护模板目录时，用它确认 renderer 会读取哪些字段、每个字段表示什么、允许什么值形状。任务式流程见 :doc:`../../how_to/templates/index_zh`；设计解释见 :doc:`../../explanations/template_rendering/index_zh`。

文件契约
--------

模板目录可以包含 ``config.yaml``。空文件会按空 mapping 处理；如果没有 ``expr_styles.default``，renderer 会自动创建默认表达式样式。未知顶层键会 fail fast。

允许的顶层键如下：

.. list-table:: ``config.yaml`` 顶层键
   :header-rows: 1

   * - 键
     - 类型
     - 作用
   * - ``expr_styles``
     - mapping
     - 注册 ``expr_render`` 使用的表达式渲染样式。
   * - ``stmt_styles``
     - mapping
     - 注册 ``stmt_render`` 和 ``stmts_render`` 使用的操作语句渲染样式。
   * - ``globals``
     - mapping
     - 通过 ``pyfcstm.render.func.process_item_to_object`` 添加 Jinja2 globals。
   * - ``filters``
     - mapping
     - 通过同一对象加载机制添加 Jinja2 filters。
   * - ``tests``
     - mapping
     - 通过同一对象加载机制添加 Jinja2 tests。
   * - ``ignores``
     - string list
     - gitignore 风格的模板目录忽略规则。

表达式样式
----------

``expr_styles`` 下每个条目都是 mapping，必须包含 ``base_lang``，并可为该语言样式提供模板覆盖。

.. code-block:: yaml

    expr_styles:
      python:
        base_lang: python
      c:
        base_lang: c

模板中这样使用：

.. code-block:: jinja

    {{ transition.guard | expr_render(style='python') }}
    {{ operation.value | expr_render(style='c') }}

已知表达式样式族包括 ``dsl``、``c``、``cpp``、``python``、``java``、``js``、``ts``、``rust`` 和 ``go``。

语句样式
--------

``stmt_styles`` 面向操作语句。静态语言模板可补充临时变量和类型别名设置。

.. code-block:: yaml

    stmt_styles:
      python:
        base_lang: python
      c:
        base_lang: c
        temp_type_aliases:
          int: int32_t
          float: double

生成 runtime 代码时使用：

.. code-block:: jinja

    {{ action.operations | stmts_render(style='python') }}
    {{ operation | stmt_render(style='c') }}

不要把 ``operation_stmt_render`` 或 ``operation_stmts_render`` 用作目标语言 runtime 代码生成；它们用于 DSL echo 文本。

对象加载字段
------------

``globals``、``filters`` 和 ``tests`` 使用同一对象加载约定。它们适合放 renderer 侧命名、格式化或小型辅助逻辑。目标 runtime 语义应留在生成代码或模板宏中，不应隐藏在 Python callback 里。

忽略规则
--------

``ignores`` 通过 ``pathspec`` 使用 gitignore 风格规则。renderer 总会忽略 ``.git``。作者笔记、草稿、fixtures 等不应进入生成输出的文件可放在这里。

.. code-block:: yaml

    ignores:
      - README.template-notes.md
      - testdata/
      - '*.draft'

最小配置
--------

一个最小自定义模板可以从空 mapping 开始：

.. code-block:: yaml

    {}

只有在需要目标语言表达式或语句渲染时，再逐步加入样式。

验证清单
--------

* 根值必须是 mapping。
* 只使用允许的顶层键。
* 每个自定义 style 都要有 ``base_lang``。
* 目标语言源码片段优先放在模板或宏中。
* 配置变化应配套一个小型 render 测试或生成产物检查。
