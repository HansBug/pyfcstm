.. _sec-how-to-grammar-editor-zh:

语法和编辑器任务
================

当你修改 FCSTM 语法、高亮或编辑器支持时使用本指南。精确文件地图和命令列表见
:doc:`../../reference/grammar_tooling/index_zh`；设计原因见 :doc:`../../explanations/grammar_tooling/index_zh`。

先判断修改类型
--------------

.. list-table:: 修改类型
   :header-rows: 1

   * - 修改
     - 必须更新
     - 通常也要更新
   * - 新增可解析语法
     - ANTLR 语法、生成的解析器输出、监听器/AST/模型导入、测试、领域特定语言（DSL）文档。
     - Pygments、TextMate、VSCode 诊断/补全/悬停说明。
   * - 新增关键字或操作符拼写
     - 词法语法、需要规则时的解析语法、高亮器、编辑器验证。
     - DSL 参考示例和 大语言模型（LLM）语法指南。
   * - 修改既有语法的语义解释
     - 模型导入/验证、模拟器或渲染器行为、测试、语义文档。
     - 如果编辑器反馈变化，也更新编辑器诊断。
   * - 只修正高亮
     - Pygments 或 TextMate 资产、编辑器验证。
     - 当文档示例教错形式时更新示例。
   * - 修改 VSCode 作者功能
     - VSCode TypeScript 提供器和对应验证套件。
     - 如果功能依赖词法分类，也更新 TextMate 语法。

修改解析语法
------------

1. 编辑 ``pyfcstm/dsl/grammar/GrammarParser.g4`` 和/或 ``pyfcstm/dsl/grammar/GrammarLexer.g4``。
2. 重新生成 ANTLR 输出：

   .. code-block:: bash

      make antlr_build

3. 如果解析树形状或 AST 节点形状变化，更新 ``pyfcstm/dsl/listener.py`` 和 ``pyfcstm/dsl/node.py``。
4. 如果构造有语义含义，更新模型导入和验证。
5. 添加测试，证明接受形式和拒绝形式。
6. 当用户语法或提示词语法变化时，更新用户 DSL 文档和打包 LLM 语法指南。

操作符和关键字顺序
------------------

新增操作符时，词法和高亮规则中长标记要排在短前缀之前。例如：

* ``**`` 在 ``*`` 之前；
* ``<<`` 在 ``<`` 之前；
* ``<=`` 和 ``>=`` 在 ``<`` 和 ``>`` 之前；
* ``==`` 和 ``!=`` 在 ``=`` 和 ``!`` 之前；
* ``&&`` 和 ``||`` 在单字符形式之前。

新增关键字时，在同一个修改里更新语法和所有语法展示层。能解析但不高亮的关键字，会造成文档和编辑器漂移。

同步高亮
--------

语法或关键字变化后，同时更新两类高亮：

1. ``pyfcstm/highlight/pygments_lexer.py``，用于 Sphinx 和 Python 侧高亮。
2. ``editors/fcstm.tmLanguage.json``，用于 TextMate 兼容编辑器。
3. 运行编辑器/高亮验证命令：

   .. code-block:: bash

      python editors/validate.py

如果文档 PR 没有运行编辑器命令，要在 PR 评论里明说。语法或编辑器行为变化不应静默跳过该命令。

更新 VSCode 支持
----------------

作者体验变化时，检查 ``editors/vscode/``。常见位置包括：

* ``src/diagnostics.ts``：语法诊断和 Problems 面板反馈；
* ``src/symbols.ts``：Outline 和面包屑；
* ``src/completion.ts``：关键字和符号补全；
* ``src/hover.ts``：悬停说明；
* ``snippets/fcstm.code-snippets``：用户片段。

涉及打包行为时构建扩展包：

.. code-block:: bash

   make vscode

``make vscode_clean`` 只用于清理本地扩展构建输出。

验证 Python 和 Sphinx 高亮
--------------------------

Python 工具侧，确认 Pygments 别名可见：

.. code-block:: bash

   python -c "from pygments.lexers import get_lexer_by_name; print(get_lexer_by_name('fcstm'))"

Sphinx 页面中使用 ``.. code-block:: fcstm`` 示例；可见文档变化时构建双语文档：

.. code-block:: bash

   NO_CONTENTS_BUILD=1 READTHEDOCS_LANGUAGE=en sphinx-build -b html docs/source /tmp/pyfcstm-docs-en
   NO_CONTENTS_BUILD=1 READTHEDOCS_LANGUAGE=zh sphinx-build -b html docs/source /tmp/pyfcstm-docs-zh

如果 Sphinx 高亮失败，先检查 ``setup.py`` 和 ``docs/source/conf.py``，再改示例。

安装并验证 VSCode 扩展
----------------------

本地开发时，构建并安装 Makefile 产出的包：

.. code-block:: bash

   make vscode
   code --install-extension editors/vscode/build/fcstm-language-support-0.1.0.vsix

安装后打开 ``.fcstm`` 文件并验证：

1. 右下角语言模式是 ``FCSTM``。
2. 关键字、操作符、注释和字面量都有高亮。
3. Outline 显示变量、状态和事件。
4. 输入 ``state`` 会出现补全。
5. 悬停 ``pseudo`` 或 ``effect`` 等关键字时显示说明。
6. 故意无效的文件会在 Problems 中报告语法诊断。

运行 VSCode 验证套件
--------------------

扩展行为变化时，先运行聚焦套件，再运行汇总检查：

.. code-block:: bash

   cd editors/vscode
   make verify-p0.2  # parser integration
   make verify-p0.3  # syntax diagnostics
   make verify-p0.4  # document symbols
   make verify-p0.5  # completion support
   make verify-p0.6  # hover documentation
   make verify

只改语法说明的文档更新，可以记录没有运行 Node.js 支持的检查；解析器或编辑器变化应包含相关套件。

更新面向提示词的语法指南
------------------------

语法或解析规则变化时，更新打包 LLM 语法指南：

.. code-block:: bash

   make sha256
   SKIP_SLOW_TESTS=1 make unittest RANGE_DIR=./llm

Markdown 指南和校验和要一起提交。如果语法指南没有变化，记录它为何不在修改范围内。

语法修改实战路径
----------------

用下面的路径判断一次语法变化需要牵动多少工具链。

.. list-table:: 语法修改路径
   :header-rows: 1

   * - 修改类型
     - 至少检查的文件
     - 必跑检查
     - 跳过后的常见失败
   * - 新增解析关键字或操作符。
     - ``GrammarLexer.g4``、``GrammarParser.g4``、``pyfcstm/highlight/pygments_lexer.py``、``editors/fcstm.tmLanguage.json``、文档和 LLM 指南。
     - ``make antlr_build``；``python editors/validate.py``；相关解析器/模型测试；LLM 指南变化时 ``make sha256``。
     - 解析器接受文本，但高亮器或 LLM 指南仍教授错误规则。
   * - 改变解析树形状。
     - 语法文件、生成解析器输出、``pyfcstm/dsl/listener.py``、``pyfcstm/dsl/node.py``、模型导入/导出代码。
     - 解析器测试和模型导入/导出测试。
     - 语法能解析，但 AST/模型转换丢失数据。
   * - 增加编辑器作者功能。
     - TextMate 语法、``editors/vscode/src/*``、片段、验证套件。
     - ``make vscode`` 和目标 ``make verify-p0.*`` 套件。
     - VSCode 建议 Python 模型导入会拒绝的语法。
   * - 只更新示例或文档措辞。
     - 人类文档；语法建议变化时还包括提示词语法指南。
     - Sphinx 构建、示例解析命令；指南内容变化时 ``make sha256``。
     - 人类文档和大语言模型提示词漂移。

具体审查清单
~~~~~~~~~~~~

请求 review 前，在 PR body 或 comment 里贴出：

* 改了哪些语法文件，或明确语法文件未改；
* 是否重新生成解析器文件；
* listener/model/import/export 是否改变；
* 高亮/编辑器资产是否检查，或为什么不在范围内；
* LLM 语法指南和校验和决策；
* Python 和 JavaScript/编辑器测试边界决策。


记录并审查修改
--------------

进入审查前，说明：

* 新增、修改或明确拒绝的语法形式；
* 解析器/模型测试，或仅文档 验证理由；
* 高亮和编辑器验证命令；
* 重新生成的解析器或文档输出；
* 被移除或重定向的旧示例。

只有解析器行为、模型语义、高亮、编辑器反馈、用户文档和测试讲的是同一个故事时，语法修改才算准备好。
