.. _sec-how-to-grammar-editor-zh:

语法与编辑器任务指南
====================

修改 FCSTM syntax、syntax highlighting 或 editor support 时使用本指南。准确文件路径见 :doc:`../../reference/grammar_tooling/index_zh`。

修改语法
--------

1. 编辑 ``pyfcstm/dsl/grammar/GrammarParser.g4`` 或 ``pyfcstm/dsl/grammar/GrammarLexer.g4``。
2. 运行 ANTLR 生成：

   .. code-block:: bash

      make antlr_build

3. 如果 parse tree 形状变化，更新 ``pyfcstm/dsl/listener.py`` 和 ``pyfcstm/dsl/node.py``。
4. 为语法变化添加或更新 parser/model tests。
5. prompt-facing syntax 变化时，同步更新 LLM grammar guide。

修改高亮
--------

grammar 变化后，同步 highlighters：

1. 更新 ``pyfcstm/highlight/pygments_lexer.py``。
2. 更新 ``editors/fcstm.tmLanguage.json``。
3. 多字符操作符必须放在更短前缀之前。
4. 运行：

   .. code-block:: bash

      python editors/validate.py

``editors/validate.py`` 是 editor/highlight asset 一致性的仓库级校验命令。如果 docs-only PR 只记录流程而没有运行某个工具，需要在 PR comment 中说明。

更新 VSCode 扩展
----------------

editor 行为变化时，检查 ``editors/vscode/`` 和 ``editors/jsfcstm/``。构建扩展包：

.. code-block:: bash

   make vscode

用 ``make vscode_clean`` 清理本地 extension build outputs。

记录变更
--------

语法变化应该更新用户可见 DSL reference 或 how-to 页面，而不只是 grammar 文件。维护者侧变化应更新工具链参考，并说明生成资产是否已重新生成。

进入 review 前，列出你运行的命令，以及能证明 grammar、highlighting 和 editor assets 一致的语法例子。
