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


Pygments 与 Sphinx 事实
-----------------------

package 通过 ``setup.py`` 中的 ``pygments.lexers`` entry point 注册 ``pyfcstm.highlight.pygments_lexer.FcstmLexer``。canonical alias 是 ``fcstm``；lexer 也接受 ``fcsm``。程序化调用可使用：

.. code-block:: python

   from pygments.lexers import get_lexer_by_name

   lexer = get_lexer_by_name("fcstm")

documentation build 也会在 ``docs/source/conf.py`` 中注册 lexer，并用 ``fcstm`` code blocks 展示示例。如果 Sphinx highlighting 失败，先检查 installed package entry point 和 docs configuration，再修改示例源码。

TextMate 与 editor 事实
-----------------------

仓库 TextMate grammar 是 ``editors/fcstm.tmLanguage.json``。它是 TextMate-compatible editor highlighting 的来源，并会在 VSCode extension packaging 时复制到 extension 的 ``syntaxes/`` 区域。

Sublime Text 可以使用同一个文件：在 ``Preferences -> Browse Packages`` 下放入类似 ``FCSTM`` 的 package 目录即可。

VSCode extension 事实
---------------------

VSCode extension 位于 ``editors/vscode/``。package manifest 是 ``package.json``；language configuration 是 ``language-configuration.json``；TypeScript providers 位于 ``src/``。

bundled output 位于 ``dist/``；local packages 以 ``.vsix`` 文件写入 ``build/``。

extension 提供这些 editor-facing capabilities：

.. list-table:: VSCode feature map
   :header-rows: 1

   * - Capability
     - Representative files
     - User-visible behavior
   * - Syntax diagnostics
     - ``src/diagnostics.ts``
     - Problems panel diagnostics 和 inline squiggles。
   * - Document symbols
     - ``src/symbols.ts``
     - variables、states 和 events 的 Outline 与 breadcrumb navigation。
   * - Completion
     - ``src/completion.ts``
     - keywords、constants、built-ins 和 document-local symbols 的 IntelliSense。
   * - Hover documentation
     - ``src/hover.ts``
     - event scopes、pseudo states、lifecycle keywords 和 aspect syntax 的 contextual help。
   * - Snippets
     - ``snippets/fcstm.code-snippets``
     - common variable、state、transition 和 lifecycle patterns 的短 prefixes。

本地 VSIX 安装使用标准 VSCode command-line interface：

.. code-block:: bash

   code --install-extension editors/vscode/build/fcstm-language-support-0.1.0.vsix

校验命令族
----------

VSCode Makefile 暴露 focused suites 和 aggregate ``make verify`` target。当前 focused suites 包括：

.. list-table:: VSCode verification suites
   :header-rows: 1

   * - Command
     - Focus
   * - ``make verify-p0.2``
     - Parser integration。
   * - ``make verify-p0.3``
     - Syntax diagnostics。
   * - ``make verify-p0.4``
     - Document symbols。
   * - ``make verify-p0.5``
     - Completion support。
   * - ``make verify-p0.6``
     - Hover documentation。
   * - ``make verify``
     - Aggregate extension verification，包含更新的 semantic、import、preview 和 end-to-end checks。

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
