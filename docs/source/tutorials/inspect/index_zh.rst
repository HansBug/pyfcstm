第一份 inspect 报告
========================================

本教程用一个较小但诊断较丰富的 FCSTM 文件运行 ``pyfcstm inspect``。目标不是学习每个报告字段，而是看到三种主要输出形式，并知道下一步去哪里查。

术语说明：人工报告（human report）、结构化报告（structured report）和大语言模型报告（LLM report）在本页首次交接后，后文只使用中文术语。

使用诊断较丰富的示例
----------------------------------------

已纳入文档构建的教程输入是：

.. literalinclude:: inspect_diagnostics.fcstm
   :language: fcstm

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
   print([item["code"] for item in report["diagnostics"]])

.. testoutput::

   InspectDemo
   6
   ['W_DURING_CONST_ASSIGN', 'W_COMBO_DUPLICATE_EVENT', 'W_COMBO_GUARD_PREFIX_IMPLIED', 'W_LEAF_NO_OUTGOING_TRANSITION', 'W_LEAF_NO_OUTGOING_TRANSITION', 'I_UNREFERENCED_VAR_MAYBE_ABSTRACT', 'W_UNWRITTEN_READ_VAR', 'I_UNREFERENCED_VAR_MAYBE_ABSTRACT', 'I_UNREFERENCED_VAR_MAYBE_ABSTRACT', 'I_UNREFERENCED_VAR_MAYBE_ABSTRACT', 'W_GUARD_VARS_NEVER_CHANGE', 'W_GUARD_VARS_NEVER_CHANGE', 'W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE']

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
