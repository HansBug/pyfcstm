.. _sec-explanations-grammar-tooling-zh:

语法工具链解释
==============

FCSTM syntax support 分为多个层次。ANTLR grammar 定义可解析语法，listener 将 parse tree 转换为仓库 AST nodes，独立 highlighters 让同一语法在文档和编辑器里可读。

为什么多个文件必须一起更新
--------------------------

语法变更不是让 ``.g4`` 能 parse 就结束。用户还会通过 examples、Sphinx code blocks、VSCode highlighting 和 JavaScript editor tooling 看到语法。如果这些层次漂移，就会出现 model 能 parse，但 docs 或 editor 仍在教旧语法的情况。

维护规则因此是：

* Parser grammar 定义什么有效。
* Listener 和 AST nodes 定义 Python model importer 能导入什么。
* Pygments 和 TextMate 定义人看到的 highlighting。
* Editor validation 检查 editor-facing assets 是否对齐。
* DSL docs 和 tests 定义用户可以依赖什么。


Pygments 与 TextMate 角色
-------------------------

Pygments 服务 Python 和 documentation contexts。它让 Sphinx、terminal formatters、notebooks 和其他 Python tools 能展示 FCSTM snippets，而不需要运行 model importer。

TextMate grammar 服务 editor highlighting contexts。它刻意比 parser 更轻：它应该清晰分类文本，但不应该变成第二套 semantic validator。

因此，只需要 highlighting 的例子可以留在 documentation 或 editor tooling 中；semantic examples 应放到 parser、model、simulator 或 verification tests。

VSCode 角色
-----------

VSCode extension 把 TextMate highlighting 和 parser-backed authoring features 组合起来，包括 diagnostics、document symbols、completion、hover help、snippets 和 preview support。它是 authoring aid，而不是 canonical execution engine。

syntax change 同时影响 parseability 和 editor feedback 时，应先更新 Python grammar/model path，再同步 editor diagnostics 和 completion，让用户看到的 language 与 parser 接受的 language 一致。

Parser 与 listener 边界
-----------------------

ANTLR 生成文件不应包含手写行为。仓库逻辑应放在 listener、node、model 或 validation code 中。这样 ``make antlr_build`` 重写生成 parser outputs 时不会丢手工修改。

Highlighting 边界
-----------------

Syntax highlighting 应跟随 grammar facts，而不是发明语法。highlighter 可以在模糊文本上保守，但不应宣传 parser 会拒绝的 keyword、operator 或 block form。

Editor tooling 边界
-------------------

JavaScript 和 VSCode assets 支持 authoring workflows。它们应与 Python 单元测试 fixtures 保持独立。两侧需要同一语法场景时，在各自 test tree 中复制最小 DSL 例子，而不是互相 import 对方 tests。

这种分离保证 Python tests 不需要 Node.js 也能运行，也保证 editor tests 不依赖仓库级 Python test tree。
