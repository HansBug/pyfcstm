.. _sec-reference-grammar-tooling-zh:

语法与编辑器工具链参考
======================

本页是 FCSTM grammar、syntax highlighting 和 editor 维护的事实地图。更新流程见 :doc:`../../how_to/grammar_editor/index_zh`；设计解释见 :doc:`../../explanations/grammar_tooling/index_zh`。

权威文件
--------

.. list-table:: 语法与编辑器文件
   :header-rows: 1

   * - 区域
     - 路径
     - 说明
   * - Parser grammar
     - ``pyfcstm/dsl/grammar/GrammarParser.g4``
     - FCSTM DSL parser rules 的权威来源。
   * - Lexer grammar
     - ``pyfcstm/dsl/grammar/GrammarLexer.g4``
     - tokens、keywords、literals 和 operators 的权威来源。
   * - Python parser output
     - ``pyfcstm/dsl/grammar/``
     - ANTLR 生成的 Python 文件；用 ``make antlr_build`` 刷新。
   * - DSL listener
     - ``pyfcstm/dsl/listener.py``
     - 把 parse events 转换为 AST nodes。
   * - DSL AST nodes
     - ``pyfcstm/dsl/node.py``
     - Syntax tree dataclasses 和导出 helpers。
   * - Pygments lexer
     - ``pyfcstm/highlight/pygments_lexer.py``
     - 文档和 Python 侧 syntax highlighting。
   * - TextMate grammar
     - ``editors/fcstm.tmLanguage.json``
     - 编辑器共享 highlighting grammar。
   * - Editor validation
     - ``editors/validate.py``
     - editor/highlight assets 的仓库校验命令。
   * - JavaScript frontend
     - ``editors/jsfcstm/``
     - editor integrations 使用的 JavaScript parser/runtime assets。
   * - VSCode extension
     - ``editors/vscode/``
     - VSCode 打包和扩展集成。

核心命令
--------

.. list-table:: 维护命令
   :header-rows: 1

   * - 命令
     - 作用
   * - ``make antlr``
     - 需要时下载或设置 ANTLR 支持。
   * - ``make antlr_build``
     - 修改 ``GrammarParser.g4`` 或 ``GrammarLexer.g4`` 后重新生成 parser outputs。
   * - ``python editors/validate.py``
     - 校验 syntax highlighting 和 editor asset 一致性。
   * - ``make vscode``
     - 构建 VSCode extension package。
   * - ``make vscode_clean``
     - 清理 VSCode extension build artifacts。

操作符顺序事实
--------------

Lexer patterns 和 highlighters 应把多字符操作符放在单字符前缀之前。例如 ``**`` 在 ``*`` 前，``<<`` 在 ``<`` 前，``<=`` 在 ``<`` 前，``>=`` 在 ``>`` 前，``==`` 在 ``=`` 前，``!=`` 在 ``!`` 前，``&&`` / ``||`` 在单字符前缀之前。

关键词更新清单
--------------

语法新增 keyword 或 operator 时，应同步更新：

1. ``pyfcstm/dsl/grammar/`` 下的 ANTLR grammar files。
2. 通过 ``make antlr_build`` 生成 parser outputs。
3. parse tree 形状变化时更新 listener 和 AST handling。
4. Pygments lexer groups。
5. TextMate grammar keyword/operator patterns。
6. Editor validation expectations。
7. 用户可见语法变化对应的 DSL guide 和 tests。

不要把生成 parser 路径写成源码权威来源。``.g4`` 文件是源，生成 parser 文件是输出。
