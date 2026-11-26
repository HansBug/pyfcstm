第一份 inspect 报告
========================================

本教程用一个较小但诊断较丰富的 FCSTM 文件运行 ``pyfcstm inspect``。目标不是学习每个报告字段，而是看到三种主要输出形式，并知道下一步去哪里查。

术语说明：人工报告（human report）、结构化报告（structured report）和大语言模型报告（LLM report）在本页首次交接后，后文只使用中文术语。

使用诊断较丰富的示例
----------------------------------------

已纳入文档构建的教程输入如下。请把 :download:`inspect_diagnostics.fcstm <inspect_diagnostics.fcstm>` 下载到一个空目录，再在那里运行命令：

.. literalinclude:: inspect_diagnostics.fcstm
   :language: fcstm
   :linenos:

它是合法 DSL。里面的警告是有意安排的教学信号，不是解析失败。

先运行人工报告输出
----------------------------------------

.. code-block:: console

   $ pyfcstm inspect -i inspect_diagnostics.fcstm --color never
   [WARN] FCSTM Inspect Report: inspect_diagnostics.fcstm

   Summary
     status: warning
     root: InspectDemo
   ...
   [WARN] W_DURING_CONST_ASSIGN
     During action in 'InspectDemo.Active' assigns 'counter' to the same constant value every cycle.
     --> inspect_diagnostics.fcstm:12:13
   ...

人类可读渲染器用于阅读。它会展示诊断码、严重级别、信息、可用的源码摘录，以及部分结构化 ``refs``。

导出完整 JSON
----------------------------------------

脚本需要结构事实时使用完整 JSON：

.. code-block:: console

   $ pyfcstm inspect -i inspect_diagnostics.fcstm --format json -o inspect.json

.. testcode::

   import json
   from pathlib import Path

   report = json.loads(Path("inspect.json").read_text())
   print(report["root_state_path"])
   print(len(report["states"]))
   for item in report["diagnostics"]:
       print(item["span"]["line"], item["code"])

.. testoutput::

   InspectDemo
   6
   12 W_DURING_CONST_ASSIGN
   19 W_COMBO_DUPLICATE_EVENT
   20 W_COMBO_GUARD_PREFIX_IMPLIED
   15 W_LEAF_NO_OUTGOING_TRANSITION
   16 W_LEAF_NO_OUTGOING_TRANSITION
   1 I_UNREFERENCED_VAR_MAYBE_ABSTRACT
   2 W_UNWRITTEN_READ_VAR
   3 I_UNREFERENCED_VAR_MAYBE_ABSTRACT
   4 I_UNREFERENCED_VAR_MAYBE_ABSTRACT
   5 I_UNREFERENCED_VAR_MAYBE_ABSTRACT
   20 W_GUARD_VARS_NEVER_CHANGE
   20 W_GUARD_VARS_NEVER_CHANGE
   4 W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE

前两行之后，每一行是一条诊断：先是它指向的模型行号，再是诊断码。对照上面带行号的模型：第 12 行是常量的 ``during`` 赋值，第 19 行是重复的 ``Confirm`` 项，第 20 行是组合触发的守卫项，第 15 和 16 行是两个没有出边的叶子状态，第 1 到 5 行是变量声明，第 4 行是对 C 目标来说过大的字面量。

这个格式是完整 ``ModelInspect`` 契约。字段说明见 :doc:`../../reference/inspect_report/index_zh`。

导出大语言模型修复报告
----------------------------------------

修复循环需要紧凑指导而不是完整结构清单时，使用 ``llm-json``：

.. code-block:: console

   $ pyfcstm inspect -i inspect_diagnostics.fcstm --format llm-json -o inspect.llm.json

大语言模型报告包含修复协议、源码摘录、``refs``、注册表摘要、建议动作和禁止做法。它故意比完整 JSON 更小。

记住无效输入边界
----------------------------------------

检查报告只会在文件可读取、可解析并能转换成模型之后产生。缺失文件、语法错误和重复状态名这类硬模型构建错误都是命令行失败，不是带 ``diagnostics`` 数组的成功报告。因此有些注册表 ``E_*`` 诊断码描述的是受控校验错误形状，而不是检查 JSON 条目。可以用不存在的文件观察这个边界：

.. code-block:: console

   $ pyfcstm inspect -i does-not-exist.fcstm
   Input DSL file not found: does-not-exist.fcstm
   $ echo $?
   1

当诊断码参考页把示例标为 ``cli_error`` 时，应预期同样的非零命令边界，并断言错误输出和退出状态，而不是 ``diagnostics[]``。

下一步
----------------------------------------

* CI、大语言模型和验证支持的任务做法见 :doc:`../../how_to/inspect/index_zh`。
* Inspect 能证明什么、不能证明什么见 :doc:`../../explanations/diagnostics/index_zh`。
* 已有具体诊断码时查 :doc:`../../reference/diagnostics_codes/index_zh`。
* 在含区域的模型上观察区域顺序诊断 ``I_REGION_BACKWARD_READ``，见 :doc:`../../tutorials/regions/index_zh`。
