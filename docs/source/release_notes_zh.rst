版本说明
========

v0.5.0
------

本版本应作为 minor release 发布，而不是 ``v0.4.2`` 这类 patch release。
它增加了新的用户可见 API、CLI 能力、打包的 LLM 资源、接入验证能力的诊断、
DSL 条件表达式运算符，以及模拟器语义修复。已有模型升级前应先阅读兼容性说明。

验证与 inspect
~~~~~~~~~~~~~~

- 新增 :mod:`pyfcstm.verify` 包，作为原始验证算法、注册表元数据、复杂度分类
  和 inspect 接入门控的公开入口。
- 新增面向 guard、effect、生命周期关系、transition shadowing 和 composite
  initialization 的 SMT 局部验证算法。
- 将 inspect 允许调用的验证算法接入
  :func:`pyfcstm.diagnostics.inspect_model` 和 ``pyfcstm inspect`` CLI。
  默认 inspect 分析路径仍不运行验证；需要通过 ``enable_verify=True`` 或
  ``pyfcstm inspect --enable-verify`` 显式启用。
- 增加复杂度层级、调用次数扩展方式和 SMT timeout 转发的安全门控。BMC 风格
  搜索仍不进入自动 inspect 路径。

诊断与 CLI
~~~~~~~~~~

- 结构化诊断目录扩展到 59 个代码：20 个 error、32 个 warning、7 个 info。
- 增加 verify-backed diagnostics，同时保持默认 inspect 分析路径为静态分析。
- 新增 ``pyfcstm inspect``，默认输出人类可读诊断报告；通过 ``--format json``
  继续输出与 ``inspect_model(model).to_json()`` 对齐的稳定 JSON 报告。
- 将默认 human inspect 报告改进为带相邻源码上下文的 checker-style 诊断布局，
  并新增 ``--color auto|always|never`` 控制 ANSI 颜色，同时保证文件、pipe 和机器格式
  不含 ANSI escape。
- 保持 Python / jsfcstm 在 normalized code、severity 和 refs payload 上的
  诊断表面一致性，供编辑器集成复用。

LLM 语法指南
~~~~~~~~~~~~

- 新增 :mod:`pyfcstm.llm`，提供
  :func:`pyfcstm.llm.get_grammar_guide_prompt_for_llm`、
  :func:`pyfcstm.llm.get_grammar_guide_prompt_path_for_llm` 和
  :func:`pyfcstm.llm.get_grammar_guide_prompt_metadata_for_llm`。
- 将官方 LLM-facing FCSTM grammar guide 打包为
  ``pyfcstm/llm/fcstm_grammar_guide.md``。
- 为 grammar guide prompt 增加打包的 SHA-256 sidecar 和运行时完整性校验。
  调用方如果确实需要检查损坏资源或开发态资源，可以选择将完整性失败降级为
  warning。
- 新增独立的 ``llm_eval/`` fixtures 和 reports，用于 prompt 质量验证。这些
  是仓库评测资料，不会打包进 PyPI 分发物。

模拟器与内置模板
~~~~~~~~~~~~~~~~

- 强化模拟器在 speculative rollback、hot-start initialization、event
  normalization、lifecycle action refs、abstract handler contracts 和 cycle
  boundary 行为上的语义。
- 增加模拟器与生成运行时对齐的 semantic fixture corpus。
- 稳定生成的 Python runtime metadata、callback rollback 行为和 expression
  error wrapping。
- 打包内置模板仍通过 ``pyfcstm generate --template ...`` 使用。当前打包模板为
  ``python``、``c`` 和 ``c_poll``；VSCode 扩展有独立版本线，本 Python 包
  发布不会把 VSCode 扩展版本改为 ``0.5.0``。

DSL 表达式运算符
~~~~~~~~~~~~~~~~

本版本为 ``cond_expression`` 增加三组可用于守卫条件和其他布尔表达式位置的
布尔运算符：

- ``A => B`` 和 ``A implies B`` 表示蕴含。规范化 DSL 写法是 ``=>``。
  蕴含是右结合，因此 ``A => B => C`` 表示 ``A => (B => C)``。
- ``A xor B`` 表示布尔异或。链式 ``xor`` 是左结合的布尔奇偶异或链，
  不是多个输入中恰好一个为真的 exactly-one 运算。
- ``A iff B`` 表示布尔等价，是布尔相等关系的可读写法。链式 ``iff`` 与布尔
  ``==``、``!=`` 使用同一相等关系优先级层。

兼容性说明
~~~~~~~~~~

``implies``、``xor`` 和 ``iff`` 现在是 DSL 保留关键字。已有状态机如果把这些
名字用作变量、状态或事件名，需要在使用本版本前先重命名。

``->`` 仍然是状态转换箭头，不是守卫条件中的蕴含运算符。请使用 ``=>`` 或
``implies``。

``^`` 仍然是数值位异或运算符。它可以出现在守卫中被比较的算术表达式里，例如：

.. code-block:: fcstm

   StateA -> StateB : if [(flags ^ 0xFF) == 0];

它不是布尔异或写法：

.. code-block:: fcstm

   StateA -> StateB : if [a > 0 xor b > 0];   // 有效
   StateA -> StateB : if [(a > 0) ^ (b > 0)]; // 无效
   StateA -> StateB : if [true ^ false];      // 无效

验证与 inspect API 是本版本新增的公开能力。函数入口和 JSON 契约会作为稳定
接口维护，但精确诊断文案和 solver evidence 文本应视为诊断 payload，不建议
下游用字符串解析方式硬编码依赖。
