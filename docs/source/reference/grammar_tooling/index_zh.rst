.. _sec-reference-grammar-tooling-zh:

语法和编辑器工具参考
====================

本页是 FCSTM 语法、高亮和编辑器维护的精确地图。任务流程见 :doc:`../../how_to/grammar_editor/index_zh`；
设计原因见 :doc:`../../explanations/grammar_tooling/index_zh`。

本页中文术语约定：解析器（parser）、词法器（lexer）、监听器（listener）、生成文件（generated file）、
语法高亮（syntax highlighting）、编辑器验证（editor validation）、验证套件（verification suite）和校验和（checksum）
首次在这里对应英文；后文普通说明使用中文术语。ANTLR、Pygments、TextMate、VSCode、LLM、命令和路径保持原文。

规范源文件和生成文件
--------------------

.. list-table:: 语法和编辑器文件
   :header-rows: 1

   * - 区域
     - 路径
     - 源文件或生成物
     - 说明
   * - 解析语法
     - ``pyfcstm/dsl/grammar/GrammarParser.g4``
     - 源文件
     - FCSTM 构造的解析规则。
   * - 词法语法
     - ``pyfcstm/dsl/grammar/GrammarLexer.g4``
     - 源文件
     - 标记、关键字、字面量和操作符。
   * - Python 解析器输出
     - ``pyfcstm/dsl/grammar/``
     - 生成物
     - 由 ``make antlr_build`` 重新生成；不要手改生成的解析器文件。
   * - 领域特定语言（DSL）监听器
     - ``pyfcstm/dsl/listener.py``
     - 源文件
     - 把解析事件转换成 AST 节点。
   * - DSL AST 节点
     - ``pyfcstm/dsl/node.py``
     - 源文件
     - 语法树数据类和导出辅助函数。
   * - 模型导入器
     - ``pyfcstm/model/imports.py`` 及相关 ``pyfcstm/model/`` 模块
     - 源文件
     - 把 AST 节点转换成语义模型对象和诊断。
   * - Pygments 词法器
     - ``pyfcstm/highlight/pygments_lexer.py``
     - 源文件
     - 文档和 Python 侧语法高亮。
   * - TextMate 语法
     - ``editors/fcstm.tmLanguage.json``
     - 源文件
     - TextMate 兼容高亮语法。
   * - 编辑器验证
     - ``editors/validate.py``
     - 源命令
     - 验证高亮/编辑器资产一致性。
   * - JavaScript 前端
     - ``editors/jsfcstm/``
     - 源文件和本地生成资产
     - 编辑器集成使用的 JavaScript 解析器/运行时资产。
   * - VSCode 扩展
     - ``editors/vscode/``
     - 源文件和构建输出
     - VSCode 打包和作者功能。
   * - 大语言模型（LLM）语法指南
     - ``pyfcstm/llm/fcstm_grammar_guide.md``
     - 提示词源资产
     - 语法变化时更新，并用 ``make sha256`` 刷新 ``.sha256``。

核心维护命令
------------

.. list-table:: 命令
   :header-rows: 1

   * - 命令
     - 目的
     - 典型触发
   * - ``make antlr``
     - 需要时下载/设置 ANTLR 支持。
     - 首次本地语法维护设置。
   * - ``make antlr_build``
     - 编辑 ``GrammarParser.g4`` 或 ``GrammarLexer.g4`` 后重新生成解析器输出。
     - 任意语法文件变化。
   * - ``python editors/validate.py``
     - 验证语法高亮和编辑器资产一致性。
     - 语法、关键字、操作符、Pygments 或 TextMate 变化。
   * - ``make vscode``
     - 构建 VSCode 扩展包。
     - VSCode 包或扩展集成变化。
   * - ``make vscode_clean``
     - 移除 VSCode 扩展构建产物。
     - 本地清理。
   * - ``make sha256``
     - 刷新生成的校验和旁文件。
     - LLM 语法指南内容变化。
   * - ``SKIP_SLOW_TESTS=1 make unittest RANGE_DIR=./llm``
     - 验证 LLM 指南打包和校验和行为。
     - LLM 指南或提示词资产变化。

Pygments 和 Sphinx 事实
-----------------------

包通过 ``setup.py`` 中的 ``pygments.lexers`` 入口注册 :class:`pyfcstm.highlight.pygments_lexer.FcstmLexer`。
规范别名是 ``fcstm``；词法器也接受 ``fcsm``。

程序化加载检查：

.. code-block:: python

   from pygments.lexers import get_lexer_by_name

   lexer = get_lexer_by_name("fcstm")

Sphinx 也在 ``docs/source/conf.py`` 中注册该词法器。面向用户的 FCSTM 示例应使用：

.. code-block:: rst

   .. code-block:: fcstm

      state Root {
          state Idle;
          [*] -> Idle;
      }

TextMate 事实
-------------

仓库 TextMate 语法是 ``editors/fcstm.tmLanguage.json``。它是 TextMate 兼容高亮的来源，并在打包时复制到 VSCode 扩展的 ``syntaxes/`` 区域。

Sublime Text 集成时，把同一文件放到 ``Preferences -> Browse Packages`` 下类似 ``FCSTM`` 的包目录中。

VSCode 扩展事实
---------------

.. list-table:: VSCode 文件地图
   :header-rows: 1

   * - 文件或目录
     - 目的
   * - ``editors/vscode/package.json``
     - 扩展清单、命令、激活、语言贡献和脚本。
   * - ``editors/vscode/language-configuration.json``
     - 注释、括号、缩进和编辑器语言行为。
   * - ``editors/vscode/src/diagnostics.ts``
     - Problems 面板诊断和行内波浪线。
   * - ``editors/vscode/src/symbols.ts``
     - Outline 和面包屑的文档符号。
   * - ``editors/vscode/src/completion.ts``
     - 关键字、常量、内置项和文档内符号补全。
   * - ``editors/vscode/src/hover.ts``
     - 事件作用域、伪状态、生命周期关键字和切面语法的上下文帮助。
   * - ``editors/vscode/snippets/fcstm.code-snippets``
     - 常见变量、状态、转换和生命周期形式的片段。
   * - ``editors/vscode/dist/``
     - 打包输出。
   * - ``editors/vscode/build/``
     - 本地 ``.vsix`` 包输出。

本地 VSIX 安装：

.. code-block:: bash

   code --install-extension editors/vscode/build/fcstm-language-support-0.1.0.vsix

VSCode 验证套件
---------------

.. list-table:: 聚焦套件
   :header-rows: 1

   * - 命令
     - 关注点
   * - ``make verify-p0.2``
     - 解析器集成。
   * - ``make verify-p0.3``
     - 语法诊断。
   * - ``make verify-p0.4``
     - 文档符号。
   * - ``make verify-p0.5``
     - 补全支持。
   * - ``make verify-p0.6``
     - 悬停说明。
   * - ``make verify``
     - 汇总扩展验证，包括较新的语义、导入、预览和端到端检查。

操作符顺序事实
--------------

词法模式和高亮器应把多字符操作符放在单字符操作符之前。

.. list-table:: 操作符顺序示例
   :header-rows: 1

   * - 较长标记
     - 必须排在其前
     - 原因
   * - ``**``
     - ``*``
     - 幂运算不能被切成两个乘法标记。
   * - ``<<``
     - ``<``
     - 位移不能被切成两个小于号标记。
   * - ``<=`` / ``>=``
     - ``<`` / ``>``
     - 比较操作符必须保留等号后缀。
   * - ``==`` / ``!=``
     - ``=`` / ``!``
     - 相等和不等不能被切成赋值或取反标记。
   * - ``&&`` / ``||``
     - ``&`` / ``|``
     - 逻辑操作符不能被切成类似按位操作符的片段。

关键字更新清单
--------------

语法变化新增关键字或操作符时，一起更新：

1. ``pyfcstm/dsl/grammar/`` 下的 ANTLR 语法文件。
2. 通过 ``make antlr_build`` 得到的解析器输出。
3. 解析树形状变化时的监听器和 AST 处理。
4. 语义含义变化时的模型导入和验证。
5. Pygments 词法器分组。
6. TextMate 语法里的关键字/操作符模式。
7. 编辑器验证期望。
8. 作者行为变化时的 VSCode 诊断、补全、悬停和片段。
9. 用户语法变化时的 DSL 指南、示例和测试。
10. 提示词语法变化时的 LLM 语法指南和校验和。

不要把生成的解析器路径写成事实来源。``.g4`` 文件是源；生成的解析器文件是输出。
