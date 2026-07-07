.. _sec-how-to-inspect-zh:

Inspect 任务指南
========================================

当你已经知道要让 inspect 完成什么任务时，使用这些做法。

为 CI 写出 JSON 报告
----------------------------------------

.. code-block:: bash

   pyfcstm inspect -i machine.fcstm --format json -o inspect.json

最小 CI 门禁通常解析文件并统计严重级别，而不是匹配人类可读信息：

.. code-block:: python

   import json
   from pathlib import Path

   report = json.loads(Path('inspect.json').read_text())
   errors = [item for item in report['diagnostics'] if item['severity'] == 'error']
   if errors:
       raise SystemExit('inspect reported blocking diagnostics')

写出 LLM 修复报告
----------------------------------------

.. code-block:: bash

   pyfcstm inspect -i machine.fcstm --format llm-json -o inspect.llm.json
   pyfcstm inspect -i machine.fcstm --format llm-md -o inspect.llm.md

当消费方需要修复指导、源码摘录和禁止做法时，使用 LLM 格式。当消费方需要状态、转换、指标和派生图的完整结构时，使用完整 JSON。

启用有界验证检查
----------------------------------------

默认 inspect 是静态检查。需要验证支持的诊断时显式启用：

.. code-block:: bash

   pyfcstm inspect -i machine.fcstm --enable-verify --format human --color never

保持策略有界。``bmc_search`` 和 ``k_unrollings`` 相关标签只是为了让 inspect 能报告受控策略错误而被 Click 接受。

控制输出文件和颜色
----------------------------------------

.. code-block:: bash

   pyfcstm inspect -i machine.fcstm --format human --color never
   pyfcstm inspect -i machine.fcstm --format json -o inspect.json
   pyfcstm inspect -i machine.fcstm --format llm-json -o repair.json

颜色只作用于 ``human``。机器可读格式会忽略 ``--color``。如果输出文件后缀看起来和格式不匹配，inspect 可以向 stderr 输出警告，同时仍写出请求的文件。

处理无效输入和策略错误
----------------------------------------

下面这些是命令行失败，不是成功检查报告：

.. list-table:: 失败边界
   :header-rows: 1
   :widths: 32 68

   * - 失败
     - 含义
   * - 文件缺失或不可读
     - 检查命令无法读取输入字节。
   * - 解码失败
     - 输入无法被支持的编码路径解码。
   * - 语法解析错误
     - 文本不是合法 FCSTM DSL。
   * - 模型校验错误
     - 已解析 DSL 违反模型层契约。
   * - 被禁止的验证策略
     - 请求的自动验证策略超出 inspect 的有界范围。

如果无效输入也需要机器可读失败报告，应在进程层包装 CLI；不要期待 ``diagnostics`` 数组。

保持目标措辞精确
----------------------------------------

有些警告是目标配置警告，不是所有运行时都会失败。例如 C 系列整数范围警告适用于生成的 ``c``、``c_poll``、``cpp`` 和 ``cpp_poll`` 部署审查。除非存在 Python 专属诊断，否则不要把它描述为 Python 运行时溢出发现。
