Inspect 与诊断
==============

``pyfcstm inspect`` 是面向文档和工具链的模型检查入口，用来回答“这段 FCSTM 最终变成了什么模型”。它会构建与仿真、可视化和代码生成相同的状态机模型，然后报告模型结构、指标、派生图、组合 trigger provenance 和诊断信息。

适合使用它的场景包括：

- 在生成目标语言代码前审查模型；
- 为 CI、编辑器或下游工具导出结构化报告；
- 给 LLM 提供精确源码区间和修复提示；
- 可选运行适合自动 inspect 的 verify 检查子集。

它不能替代仿真、目标硬件测试或完整形式化验证。无效 DSL 输入仍然是 CLI 解析/加载失败，而不是一份成功的 JSON inspect 报告。

诊断较丰富的示例
----------------------------------------

下面的示例模型刻意包含多种问题：常量 ``during`` 赋值、重复的组合事件、被前置条件蕴含的组合守卫、没有出口的叶状态、未引用变量，以及一个 C/C++ deployment-profile 数值风险。

.. literalinclude:: inspect_diagnostics.fcstm
   :language: fcstm
   :caption: inspect_diagnostics.fcstm

默认是人类可读输出
----------------------------------------

本地阅读时，不带 ``--format`` 运行 ``inspect``：

.. code-block:: bash

   pyfcstm inspect -i inspect_diagnostics.fcstm

human renderer 会先汇总模型，再用 checker-style 形式输出诊断、源码摘录、provenance、建议动作和 do-not notes：

.. literalinclude:: inspect_human.demo.sh.txt
   :language: text
   :caption: human inspect 输出摘录
   :lines: 1-40

``--color always`` / ``--color never`` 只影响 human renderer。机器格式永远不包含 ANSI color escape。

输出格式和文件
----------------------------------------

``-o`` 只决定报告写到哪里，不决定报告格式。脚本需要 JSON 或 LLM-oriented report 时，务必显式传入 ``--format``。

.. list-table:: inspect 输出格式
   :header-rows: 1

   * - 格式
     - 目标读者
     - 说明
   * - ``human``
     - 终端里阅读的人
     - 默认格式；包含源码摘录、修复提示和可选 ANSI color。
   * - ``json``
     - CI、编辑器和程序化集成
     - 完整报告，匹配 ``inspect_model(model).to_json()``。
   * - ``llm-json``
     - 偏好结构化数据的 LLM 修复循环
     - 稳定 schema ``pyfcstm.inspect.llm.v1``，包含摘要化修复字段。
   * - ``llm-md``
     - LLM prompt 和 issue comment
     - 同一 LLM-oriented repair contract 的 Markdown 版本。

常用命令：

.. code-block:: bash

   pyfcstm inspect -i inspect_diagnostics.fcstm --format json -o report.json
   pyfcstm inspect -i inspect_diagnostics.fcstm --format llm-json -o report.llm.json
   pyfcstm inspect -i inspect_diagnostics.fcstm --format llm-md -o report.llm.md

生成出来的 demo 会确认几个关键结构：

.. literalinclude:: inspect_formats.demo.sh.txt
   :language: text
   :caption: 由真实 inspect 输出生成的格式摘要
   :lines: 1-12

默认 JSON diagnostic 对象当前的顶层 key 是 ``code``、``severity``、``message``、``span`` 和 ``refs``。有些诊断会把建议编辑放在 ``refs.suggested_fix``，它不是 JSON diagnostic 的顶层字段。同理，``for_llm`` 是 registry metadata，用来渲染 LLM 格式，不是 ``--format json`` 直接输出的字段。

LLM 格式会暴露 ``summary``、``recommended_actions``、``do_not`` 和 ``repair_guidance`` 等面向修复的字段：

.. literalinclude:: inspect_formats.demo.sh.txt
   :language: text
   :caption: 由真实 inspect 输出生成的 LLM report 结构
   :lines: 14-19

如果文件后缀看起来可疑，CLI 会给出 warning，但仍然尊重用户请求的格式：

.. literalinclude:: inspect_cli_edges.demo.sh.txt
   :language: text
   :caption: color 与后缀边界检查

无效输入是 CLI 错误
----------------------------------------

语法错误和模型加载失败会以非零退出码报告。即便用户传入 ``--format json``，inspect 也不会为无法解析或无法加载的输入伪造一份成功的 ``diagnostics[]`` payload。

.. literalinclude:: inspect_invalid.demo.sh.txt
   :language: text
   :caption: 无效输入边界

这个边界对自动化很重要：parse/model-load 失败应当停止流水线；而有效模型上的 diagnostics 才适合按 severity 和 code 分流处理。

组合 trigger provenance
----------------------------------------

组合 trigger 会在模型构建阶段展开为生成的伪状态链。完整 JSON 报告包含 ``combo_transitions`` 和 ``combo_origins``，所以下游工具可以把生成边重新关联回用户手写的 trigger 项。

在示例模型中：

.. code-block:: fcstm

   Active -> ComboDone :: Confirm + Confirm;
   Active -> Done : [ready > 0] + [ready > -1] effect {
       ratio = ratio + 1.0;
   };

``inspect`` 会报告源码级组合 warning，而不是只让用户调试生成的伪状态名：

- ``W_COMBO_DUPLICATE_EVENT`` 指向第二个 ``Confirm``，并在 ``refs.first_term_span`` 中记录第一次出现的位置。
- ``W_COMBO_GUARD_PREFIX_IMPLIED`` 指向 ``[ready > -1]``，并通过 ``refs.prior_term_span`` 链接起决定作用的前置守卫。
- JSON transition 记录会携带 combo origin refs；生成的伪状态名仍然对工具和可视化可见。

这些诊断描述的是用户写出来的组合 trigger。它们不是关于 ``during before`` aspect 会在 combo relay pseudo state 内部执行的 warning。

C/C++ deployment-profile 数值 warning
----------------------------------------

数值 warning 是 target-profile warning。例如 ``W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE`` 关注的是默认 C-family runtime profile 使用固定宽度生成整数类型。它不是与语言无关的 FCSTM 模型错误，也不应该被表述成 Python generated runtime 具有同样 overflow 行为的证据。

JSON ``refs`` 会明确说明适用范围：

.. literalinclude:: inspect_formats.demo.sh.txt
   :language: text
   :caption: 数值 warning 的目标范围
   :lines: 11-12

请把这类 warning 当成 C/C++ / ``c`` / ``c_poll`` / ``cpp`` / ``cpp_poll`` 目标的部署审查项。如果目标是 Python，通常不存在同一个固定宽度整数承载风险；但模型可能仍然有其他值得审查的设计问题。

可选 verify 支撑检查
----------------------------------------

默认情况下，``inspect`` 只运行静态诊断。需要运行符合自动检查预算的 verify 算法时，显式添加 ``--enable-verify``：

.. code-block:: bash

   pyfcstm inspect -i inspect_diagnostics.fcstm --format json \
     --enable-verify --max-complexity-tier smt_linear --smt-timeout-ms 1000

inspect 面向 verify 的旋钮刻意保持有界：

.. list-table:: inspect 可接受的 verify 选项
   :header-rows: 1

   * - 选项
     - 默认值
     - inspect 用途
     - 边界
   * - ``--enable-verify``
     - 关闭
     - 把适合 inspect 自动运行的 ``pyfcstm.verify`` 诊断追加到静态报告。
     - 最快结构化检查应保持关闭；本地或 CI 分流可以接受更高成本时再开启。
   * - ``--max-complexity-tier``
     - ``structural``
     - 限制 inspect adapter 允许运行的最高 verify 算法层级。
     - ``bmc_search`` 只会被解析成 policy error；需要 bounded-model checking
       或独立审查 proof budget 时，请使用专门的 verify workflow。
   * - ``--max-call-count-scaling``
     - ``linear_in_transitions``
     - 限制自动 inspect 中算法调用次数的增长等级。
     - ``k_unrollings`` 和 ``k_unrollings_times_branching`` 会被拒绝，因为它们需要显式 depth policy。
   * - ``--smt-timeout-ms``
     - 未设置
     - 给 SMT-local 算法透传有限的毫秒级超时。
     - ``0`` 会原样透传，并遵循 Z3 语义，表示不配置有限超时。

adapter 会明确拒绝需要更显式验证计划的旋钮，例如 ``bmc_search`` 和 ``k_unrollings`` 调用次数策略：

.. literalinclude:: inspect_verify_policy.demo.sh.txt
   :language: text
   :caption: 被拒绝的 verify policy 示例

如果需要 bounded-model checking、自定义 unrolling depth，或者需要独立审查的 proof budget，请使用专门的 verify workflow，而不是塞进快速 inspect pass。

和 LLM 辅助修复配合使用
----------------------------------------

一个实用修复循环是：

1. 运行 ``pyfcstm inspect`` 获取人类可读总览。
2. 运行 ``pyfcstm inspect -i inspect_diagnostics.fcstm --format llm-json`` 或
   ``--format llm-md``，把报告交给 assistant。
3. 要求 assistant 给出保持原意的最小源码修改。
4. 应用修改后重新运行 ``inspect`` 和相关测试。

LLM report 是很好的证据，不是自动证明。Diagnostics 可能同时包含启发式设计 warning、deployment-profile warning，以及强度不同的 verify-backed 结果，所以编辑后必须重新运行工具。

下一步
----------------------------------------

- :doc:`/tutorials/quick_start/index_zh` 展示最短 happy path。
- :doc:`/tutorials/simulation/index_zh` 解释运行时执行语义。
- :doc:`/tutorials/generation/index_zh` 展示 inspected model 如何进入内置模板。
- :doc:`/tutorials/dsl/index_zh` 在 DSL 参考中说明组合 trigger 和伪状态语法。
