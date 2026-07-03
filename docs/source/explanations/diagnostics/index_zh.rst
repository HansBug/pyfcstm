.. _sec-explanations-diagnostics-zh:

诊断解释
========

Inspect diagnostics 是模型审查证据。它们面向人类、CI job、编辑器或 LLM，说明当前 FCSTM 模型长什么样，以及哪些位置值得关注。

Inspect 能做什么
----------------

Inspect 可以报告：

* 结构指标和派生图事实；
* 带源码位置和结构化 refs 的源码级 diagnostics；
* combo-trigger provenance，把生成伪状态链关联回用户写的 trigger terms；
* 面向 LLM 的 repair guidance，把源码上下文放在建议动作附近；
* 显式开启时运行的可选 verify-backed diagnostics。

Inspect 不能证明什么
--------------------

Inspect 不能替代仿真、目标硬件测试或完整形式化验证 workflow。静态 warning 可能是保守的。LLM-oriented report 是很好的 prompt 和证据，但修改后仍然需要重新运行工具。

无效 DSL 仍然是 CLI failure
---------------------------

如果解析或模型构建失败，inspect 会以非零状态退出。这不同于“对一个有效模型成功输出 warning diagnostics”。

目标相关 warning 需要目标相关措辞
---------------------------------

提到 C-family 固定宽度整数 profile 的数值部署 warning，应解释为 C/C++ 部署风险。如果生成目标是 Python，通常不存在同一个固定宽度整数承载风险；但其他模型设计 warning 仍可能重要。

为什么 diagnostics 能帮助 LLM
-----------------------------

好的 LLM repair prompt 需要精确源码位置、provenance 和 do-not notes。Inspect 的 LLM 格式会打包这些细节，使 assistant 能提出小修改，而不是根据模糊错误消息猜测。
