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

验证 Python 和 Sphinx 高亮
--------------------------

对于 Python 工具，确认 packaged Pygments entry point 可见：

.. code-block:: bash

   python -c "from pygments.lexers import get_lexer_by_name; print(get_lexer_by_name('fcstm'))"

对于 Sphinx 页面，优先使用 ``.. code-block:: fcstm`` 示例；可见文档变化时，应构建中英文文档：

.. code-block:: bash

   NO_CONTENTS_BUILD=1 READTHEDOCS_LANGUAGE=en sphinx-build -b html docs/source /tmp/pyfcstm-docs-en
   NO_CONTENTS_BUILD=1 READTHEDOCS_LANGUAGE=zh sphinx-build -b html docs/source /tmp/pyfcstm-docs-zh

如果 lexer alias 不工作，先检查 ``setup.py`` 和 ``docs/source/conf.py``，再修改示例。

安装并验证 VSCode 扩展
----------------------

对于发布包，用下载的 ``.vsix`` 文件安装：

.. code-block:: bash

   code --install-extension fcstm-language-support-0.1.0.vsix

对于本地开发，先构建仓库 Makefile 产物，再安装：

.. code-block:: bash

   make vscode
   code --install-extension editors/vscode/build/fcstm-language-support-0.1.0.vsix

安装后打开 ``.fcstm`` 文件，并验证这些 editor behaviors：

1. 右下角 language mode 是 ``FCSTM``。
2. keywords、operators、comments 和 literals 正常高亮。
3. Outline view 显示 states、variables 和 events 的 document symbols。
4. 输入 ``state`` 时出现 completions。
5. 悬停 ``pseudo`` 或 ``effect`` 等关键字时显示帮助文本。
6. 故意打开一个 invalid 文件时，Problems panel 显示 syntax diagnostics。

运行 VSCode 校验套件
--------------------

extension behavior 变化时，先在 ``editors/vscode`` 中运行 focused suites，再运行 aggregate check：

.. code-block:: bash

   cd editors/vscode
   make verify-p0.2  # parser integration
   make verify-p0.3  # syntax diagnostics
   make verify-p0.4  # document symbols
   make verify-p0.5  # completion support
   make verify-p0.6  # hover documentation
   make verify

对于 syntax-only 文档更新，可以在 PR comment 中记录这些 Node.js-backed checks 未运行；但 grammar 或 editor behavior 变化不应静默跳过这些检查。

排查 editor 行为
----------------

改 grammar 或 editor code 前，先用这个 checklist：

* 如果 Sphinx highlighting 失败，验证 ``fcstm`` lexer alias，并在运行 Sphinx 的环境中重新安装 package。
* 如果 TextMate highlighting 失败，确认 ``editors/fcstm.tmLanguage.json`` 已安装到对应 editor package 位置，并重启 editor。
* 对 Sublime Text，在 ``Preferences -> Browse Packages`` 下创建 ``FCSTM`` package 目录，并把 ``fcstm.tmLanguage.json`` 复制进去。
* 如果 VSCode 未激活，确认 extension 已安装、文件扩展名是 ``.fcstm``，并且 language mode 是 ``FCSTM``。
* 如果 diagnostics 未显示，保存文件、检查 Problems panel，并查看 ``FCSTM Language Support`` output channel。
* 如果 completion 未显示，用 ``Ctrl+Space`` 手动触发，并确认光标不在 comment 或 string 中。

记录变更
--------

语法变化应该更新用户可见 DSL reference 或 how-to 页面，而不只是 grammar 文件。维护者侧变化应更新工具链参考，并说明生成资产是否已重新生成。

进入 review 前，列出你运行的命令，以及能证明 grammar、highlighting 和 editor assets 一致的语法例子。
